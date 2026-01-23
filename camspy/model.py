import glob
import io
import logging
import os
import pathlib
import time
from collections import deque
from datetime import datetime
from os.path import join

import cv2
import imutils
import requests

from camspy.utils import MultiCounter, ddrate


class ImageManip():

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


class VideoFile:

    def __init__(self, filename_prefix=None, directory=None, max_file_size=0, resolution=None,
                 fps=20, log_metrics=False):
        self.filename_prefix = filename_prefix
        self.directory = directory or os.getcwd()
        self.frames = []
        self.disk_size = 0
        self.max_file_size = max_file_size
        self.file_count = 0
        self.resolution = tuple(resolution or [1280, 964])
        self.logger = logging.getLogger("video")
        self.fps = fps
        self.log_metrics = log_metrics
        self.output_counter = MultiCounter(20)
        os.makedirs(self.directory, exist_ok=True)
        self.data_rate = MultiCounter(5)
        # self.sizes = deque(maxlen=7)
        self.cx = 0
        self.output_filename = None
        self.new_file()

    def new_file(self):
        self.file_count += 1
        self.output_filename = self.get_filename()
        return self.output_filename

    def get_filename(self, extension='mp4'):
        return join(self.directory, "#{}-{}-{}.{}".format(
            self.file_count, self.filename_prefix, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), extension))

    def get_filesize(self, filename):
        return round(os.stat(filename).st_size * 1e-6, 2)

    def filesize_exceeded(self):
        try:
            self.disk_size = self.get_filesize(self.output_filename)
            return round(self.disk_size) >= 10  # self.max_file_size
        except Exception as e:
            self.logger.info(e)
            return False

    def should_start_new_file(self):
        if self.filesize_exceeded():
            if self.log_metrics:
                self.cx += 1
                self.data_rate.increment()
                self.sizes.append(self.disk_size)
                self.logger.debug(
                    "Data rate: {0} GB/day // count: {1}"
                    .format(ddrate(self.data_rate.get_rate(), self.sizes), self.cx))
            return True
        return False

    # def maybe_start_new_file(self):
    #     if self.filesize_exceeded():
    #         if self.log_metrics:
    #             self.cx += 1
    #             self.data_rate.increment()
    #             self.sizes.append(self.disk_size)
    #             self.logger.debug(
    #                 "Data rate: {0} GB/day // count: {1}"
    #                 .format(ddrate(self.data_rate.get_rate(), self.sizes), self.cx))
    #         new_filename = self.get_filename()
    #         self.logger.debug(
    #             "Max size exceeded ({0}). Start new file: {1}".format(self.disk_size,new_filename))
    #         # self.start_new_file(new_filename)
    #         return new_filename

    def start_new_file(self, filename=None):
        self.output.stop()
        time.sleep(3)
        self.unlock_file()
        self.output.output_filename = self.output_filename = filename
        # self.output = FfmpegOutput(self.output_filename)

        # self.output.start()
        self.logger.debug('Restarted with {}, waiting'.format(self.output_filename))
        # time.sleep(5)

    #
    def delete_all(self):
        dir = pathlib.Path(self.output_filename).parent
        files = dir / '*.mp4'

        for file_path in glob.glob(files.absolute().as_posix()):
            self.logger.debug('Deleting {}'.format(file_path))
            os.remove(file_path)

        print(dir.absolute())

    def unlock_file(self):
        os.rename(self.output_filename, self.output_filename.replace("LOCKED-", ""))


class Connector:

    def __init__(self, config):
        self.logger = logging.getLogger("connector")
        self.host = config['host']
        self.name = config['name']
        self.timeout = config['timeout']
        self.image_url = "{0}/cameras/{1}/update".format(self.host, self.name)
        self.video_url = "{0}/store".format(self.host)

    def send_image(self, image):
        try:
            file = io.BytesIO(cv2.imencode('.jpg', image)[1])
            self.send_files(url=self.image_url, files=dict(file=file), headers={})
        except Exception as e:
            self.logger.error(e)

    def send_video(self, path):
        try:
            filesize = round(os.stat(path).st_size * 1e-6, 2)
            headers = {'Size': str(filesize)}
            file = open(path, 'rb')
            self.logger.debug("Sending video {0} ({1} MB)".format(path, filesize))
            return self.send_files(url=self.video_url, files=dict(file=file), headers=headers)
        except Exception as e:
            self.logger.error(e)

    def send_files(self, url, files, headers=None, timeout=None):
        headers = headers or {}
        timeout = timeout or self.timeout
        r = requests.post(url=url, files=files, headers=headers, timeout=timeout)
        if r.status_code != 200:
            self.logger.error(r.content)
        return True
