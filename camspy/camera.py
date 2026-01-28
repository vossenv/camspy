import logging
import time
from collections import deque

import libcamera
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.outputs import PyavOutput, SplittableOutput

from camspy.model import VideoFileHandler
from camspy.stream import StreamingHandler, StreamingServer, StreamingOutput
from camspy.utils import MultiCounter, start_thread, get_ip


# import ArducamSDK
# import picamera
# from picamera import PiCamera
# from picamera.array import PiRGBAnalysis


class Camera:

    def __init__(self, config):
        self.camera_type = config['camera']
        self.dev_id = config['device_id']
        self.frame_size = tuple(config['frame_size'])
        self.init_delay = config['init_delay']
        self.init_retry = config['init_retry']
        self.max_error_rate = config['max_error_rate']
        self.flip_horizontal = config['flip_horizontal']
        self.flip_vertical = config['flip_vertical']
        self.codec = config['codec']
        self.name = config['name']
        self.extra_info = []
        self.framerate = 30
        self.logger = logging.getLogger(self.camera_type)
        self.log_metrics = False
        self.ignore_warnings = False
        self.log_extra_info = False
        self.images = deque(maxlen=5)
        self.image_counter = MultiCounter(50)

    @classmethod
    def create(cls, config):
        cam = config['camera']
        if cam == 'picam':
            return PiCam(config)

        raise ValueError("Unknown camera type: {}".format(cam))

    def connect(self):
        self.logger.info('Connecting to camera')
        pass

    def start(self):
        self.logger.info('Starting camera')
        pass

    def stop(self):
        self.logger.info('Stopping camera')
        pass

    def restart(self):
        self.logger.info("Restarting camera")
        self.stop()
        self.start()
        self.logger.info("Restart done!")

    def next_image(self):
        if len(self.images) > 1:
            i = self.images[0].copy()
            return i

    def read_next_frame(self):
        pass

    def get_extra_label_info(self):
        return []

    def add_video_output(self, config, video_handler):
        pass


class PiCam(Camera):

    def __init__(self, config):
        super(PiCam, self).__init__(config)
        self.cam = None
        self.encoders = {}
        self.video_output = None
        self.streaming_output = None
        self.video_splitter = None
        self.video_config = None

    def connect(self):
        self.logger.info("Connecting to picamera")
        for i in range(self.init_retry):
            try:
                self.logger.info("Attempt: {}".format(i))
                self.cam = Picamera2()
                transform = libcamera.Transform(hflip=int(self.flip_horizontal), vflip=int(self.flip_vertical))
                config = self.cam.create_video_configuration(main={"size": self.frame_size}, transform=transform)
                self.cam.configure(config)
                time.sleep(self.init_delay)
                return
            except Exception as e:
                self.logger.error("Failed to connect to camera: {}: {}".format(type(e), e))
                time.sleep(self.init_delay)
                if i == self.init_retry - 1:
                    raise

    def start(self):
        self.logger.info("Starting picam [{}]".format(self.name))
        self.connect()
        for n, enc in self.encoders.items():
            self.logger.info("Starting {} encoder ".format(n))
            try:
                self.cam.start_encoder(*enc)
            except TypeError:
                self.cam.start_encoder(enc)
        self.cam.start()
        if 'mjpeg' in self.encoders:
            start_thread(self.start_mjpeg_stream)
        if 'video' in self.encoders:
            start_thread(self.start_video)

    def log_video_info(self, verb):
        video_config = self.video_config
        self.logger.info("{} video output for '{}' at {}: {} [{} kB/s @ {} fps]".format(
            verb,
            self.video_output.video_identifier,
            self.video_output.output_filename,
            'x'.join(map(str, video_config['resolution'])),
            video_config['bitrate'],
            video_config['framerate']
        ))

    def add_video_output(self, config, video_handler):
        self.video_config = video_config = config['recording']
        self.video_output = video_handler
        self.log_video_info('Configuring')
        self.video_output.delete_all()
        encoder = H264Encoder(video_config['bitrate'] * 1000, framerate=video_config['framerate'])
        pyav = PyavOutput(self.video_output.output_filename)
        self.video_splitter = SplittableOutput(output=pyav)
        encoder.output = self.video_splitter
        self.encoders['video'] = encoder

    def add_mjpeg_stream(self):
        self.streaming_output = StreamingOutput()
        web_enc = JpegEncoder()
        web_out = FileOutput(self.streaming_output)
        self.encoders['mjpeg'] = (web_enc, web_out)

    def start_mjpeg_stream(self):
        self.serve_test(output=self.streaming_output)

    def start_video(self):
        self.log_video_info("Starting")
        encoder = self.encoders.get('video')
        if encoder is None:
            raise ValueError("Cannot start video: encoder not specified")
        try:
            while True:
                time.sleep(5)
                if self.video_output.should_start_new_file():
                    new_filename = self.video_output.start_new_file()
                    self.video_splitter.split_output(PyavOutput(new_filename), wait_for_keyframe=True)
        except Exception as e:
            self.logger.warning("Recording failed: {}".format(e))
        finally:
            self.cam.stop_encoder(encoder)
            print("Stopped recording.")

    def serve_test(self, output):
        address = ('', 8000)
        self.logger.info('Webstream started at http://{}:{}'.format(get_ip(), address[1]))
        StreamingHandler.output = output
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()

    def stop(self):
        self.logger.info("Stopping picam")
        self.cam.stop_encoder()
        self.cam.stop()
        self.logger.info("Picam stopped")

    # def test_cam(self):
    #     dir = 'video'
    #     filestream = VideoFile(name='testcam', log_metrics=True, output_directory=dir)
    #     filestream.delete_all()
    #
    #     self.video_output = filestream
    #     filename = filestream.output_filename
    #     encoder1 = H264Encoder(3000000)
    #     pyav = PyavOutput(filename)
    #     splitter = SplittableOutput(output=pyav)
    #     encoder1.output = splitter
    #
    #     stream_out = StreamingOutput()
    #     web_enc = JpegEncoder()
    #     web_out = FileOutput(stream_out)
    #
    #     self.connect()
    #     self.cam.start_encoder(web_enc, web_out)
    #     self.cam.start_encoder(encoder1)
    #     self.cam.start()
    #
    #     start_thread(self.serve_test, output=stream_out)
    #
    #     self.logger.info("Recording started...")
    #     try:
    #         while True:
    #             time.sleep(5)
    #             if filestream.should_start_new_file():
    #                 self.logger.debug("Max size exceeded ({})".format(filestream.current_file_size))
    #                 filename = filestream.start_new_file()
    #                 self.logger.debug("Start new file: {}".format(filename))
    #                 self.logger.info("File count: {}".format(filestream.file_count))
    #                 splitter.split_output(PyavOutput(filename), wait_for_keyframe=True)
    #     finally:
    #         self.cam.stop_encoder()
    #         self.cam.stop()
    #         print("Stopped.")
    #
    # def test_cam_stream(self):
    #     try:
    #         address = ('', 8000)
    #         self.connect()
    #         output = StreamingOutput()
    #         self.cam.start_recording(JpegEncoder(), FileOutput(output))
    #         StreamingHandler.output = output
    #         server = StreamingServer(address, StreamingHandler)
    #         server.serve_forever()
    #         while True:
    #             print('slp')
    #             time.sleep(5)
    #     finally:
    #         self.cam.stop()
