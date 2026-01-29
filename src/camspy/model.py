import glob
import logging
import os
import shutil
import time
from collections import deque
from datetime import datetime
from os.path import join
from pathlib import Path

import cv2
import imutils
import paramiko

from camspy.utils import MultiCounter, ddrate, get_abs


class VideoFileHandler:
    def __init__(self, name, output_directory, max_video_file_size=50, log_metrics=False,
                 **kwargs):
        self.current_file_size = 0
        self.file_count = 0
        self.data_rate = MultiCounter(5)
        self.sizes = deque(maxlen=7)
        self.times = deque(maxlen=7)
        self.current_sizes = deque(maxlen=7)
        self.logger = logging.getLogger("video_file_output")
        self.log_metrics = log_metrics
        self.video_identifier = name
        self.max_video_file_size = max_video_file_size
        self.output_filename = None
        self.sftp = None

        output_directory = get_abs(Path(output_directory))
        self.output_directory = output_directory.as_posix()
        self.temp_out = get_abs(output_directory / 'temp').as_posix()
        self.finished_out = get_abs(output_directory / 'finished').as_posix()

        os.makedirs(self.output_directory, exist_ok=True)
        os.makedirs(self.temp_out, exist_ok=True)
        os.makedirs(self.finished_out, exist_ok=True)
        self.start_new_file()

    def move_to_finished(self):
        if (self.output_filename is None) or (not os.path.exists(self.output_filename)):
            return
        self.logger.debug("Moving {} to {}".format(self.output_filename, self.finished_out))
        shutil.move(self.output_filename, self.finished_out)

    def delete_all(self):
        files = get_abs(Path(self.output_directory) / '**/*.mp4')
        for file_path in glob.glob(files.as_posix(), recursive=True):
            self.logger.debug('Deleting {}'.format(file_path))
            os.remove(file_path)

    def start_new_file(self):
        self.move_to_finished()
        self.file_count += 1
        self.output_filename = self.get_filename()
        return self.output_filename

    def get_filename(self, extension='mp4'):
        return join(self.temp_out, "#{}-{}-{}.{}".format(
            self.file_count, self.video_identifier, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), extension))

    def check_file_size(self):
        try:
            self.current_file_size = round(os.stat(self.output_filename).st_size * 1e-6, 2)
            self.current_sizes.append(self.current_file_size)
            self.times.append(time.perf_counter())
            size_delta = self.current_sizes[-1] - self.current_sizes[0]
            time_delta = self.times[-1] - self.times[0]
            rate = size_delta / time_delta if len(self.times) > 1 else 0
            self.logger.debug(
                "Current file progress: {}/{}MB ({}%) {} - MB/min".format(
                    self.current_file_size,
                    self.max_video_file_size,
                    100 * self.current_file_size / self.max_video_file_size,
                    round(60 * rate, 2),
                ))
            return round(self.current_file_size) >= self.max_video_file_size
        except Exception as e:
            self.logger.info(e)
            return False

    def should_start_new_file(self):
        if self.check_file_size():
            self.logger.debug("Max size exceeded ({})".format(self.current_file_size))
            if self.log_metrics:
                self.data_rate.increment()
                self.sizes.append(self.current_file_size)
                self.logger.debug(
                    "Data rate: {0} GB/day // file count: {1}"
                    .format(ddrate(self.data_rate.get_rate(), self.sizes), self.file_count))
            return True
        return False

    def add_sftp(self, sftp):
        self.sftp = sftp

    def monitor_and_send(self):
        while True:
            time.sleep(5)
            files = get_abs(Path(self.finished_out) / '**/*.mp4')
            for file_path in glob.glob(files.as_posix(), recursive=True):
                self.sftp.send_file(file_path)


class SFTPConnector:
    def __init__(self, config):
        super(SFTPConnector, self).__init__()
        self.logger = logging.getLogger("sftp_connector")
        self.username = os.getenv('SF_USER')
        self.password = os.getenv('SF_PASS')
        self.hostname = os.getenv('SF_HOST')
        self.port = int(os.getenv('SF_PORT'))
        self.remote_dir = os.getenv('SF_REMOTE_DIR')
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=self.hostname, port=self.port, username=self.username, password=self.password)
        pass

    def send_file(self, file_to_send):
        filename = Path(file_to_send).name
        self.logger.info("Sending file: {}".format(filename))
        sftp = self.ssh_client.open_sftp()
        try:
            sftp.put(file_to_send, self.remote_dir + "/" + filename)
            self.logger.info("File {} successfully sent".format(filename))
            os.remove(file_to_send)
        except Exception as e:
            self.logger.error(e)
        finally:
            sftp.close()


class ImageManip:

    @staticmethod
    def show(image):
        cv2.imshow("stream", image)
        cv2.waitKey(5)

    @staticmethod
    def add_label(image, text, text_height, scale=1, color=(255, 255, 255), pad=10):
        y = image.shape[0] - pad

        for l in reversed(text):
            cv2.putText(image, l, (pad, y),
                        cv2.FONT_HERSHEY_DUPLEX, scale, color, 1, cv2.LINE_AA)
            y = y - (text_height + pad)
        return image

    @staticmethod
    def rotate(image, angle, resize=True):
        if angle == 0:
            return image
        if not resize or angle % 180 == 0:
            return imutils.rotate_bound(image, angle)
        h, w, _ = image.shape
        return ImageManip.resize(imutils.rotate_bound(image, angle), [w, h])

    @staticmethod
    def resize(image, dims):
        if not dims:
            return image
        if min(dims) <= 0:
            raise ValueError("Dimensions must be positive")
        return cv2.resize(image, (dims[0], dims[1]))

    @staticmethod
    def rectangle(image, dims, color=(0, 0, 0)):
        h, w, _ = image.shape
        cv2.rectangle(image, (0, h), (dims[0], h - dims[1]), color, -1)
        return image

    @staticmethod
    def crop(image, dims):
        if set(dims) == {0}:
            return image

        h, w, _ = image.shape
        top = round(dims[0] * 0.01 * h)
        left = round(dims[1] * 0.01 * w)
        bottom = round(dims[2] * 0.01 * h)
        right = round(dims[3] * 0.01 * w)

        if (w - left - right) <= 0 or (h - top - bottom) <= 0 or min(dims) < 0:
            raise ValueError("Crop dimensions exceed area or are negative")

        return image[top:h - bottom, left:w - right, :]
