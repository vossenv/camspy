import logging
import time

import libcamera
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.outputs import PyavOutput, SplittableOutput

from camspy.stream import StreamingHandler, StreamingServer, StreamingOutput
from camspy.utils import start_thread, get_ip


class Camera:

    def __init__(self, config):
        self.camera_type = config['camera']
        self.dev_id = config['device_id']
        self.frame_size = tuple(config['frame_size'])
        self.framerate = config['framerate']
        self.init_delay = config['init_delay']
        self.init_retry = config['init_retry']
        self.max_error_rate = config['max_error_rate']
        self.flip_horizontal = config['flip_horizontal']
        self.flip_vertical = config['flip_vertical']
        self.codec = config['codec']
        self.name = config['name']
        self.logger = logging.getLogger(self.camera_type)

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
        self.mjpeg_config = None

    def connect(self):
        self.logger.info("Connecting to picamera")
        for i in range(self.init_retry):
            try:
                self.logger.info("Attempt: {}".format(i))
                self.cam = Picamera2()
                transform = libcamera.Transform(hflip=int(self.flip_horizontal), vflip=int(self.flip_vertical))
                config = self.cam.create_video_configuration(
                    main={"size": self.frame_size},
                    controls={'FrameRate': self.framerate},
                    transform=transform)
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
            'x'.join(map(str, self.frame_size)),
            video_config['bitrate'],
            self.framerate
        ))

    def add_video_output(self, config, video_handler):
        self.video_config = video_config = config['recording']
        self.video_output = video_handler
        self.log_video_info('Configuring')
        self.video_output.delete_all()
        encoder = H264Encoder(video_config['bitrate'] * 1000)
        pyav = PyavOutput(self.video_output.output_filename)
        self.video_splitter = SplittableOutput(output=pyav)
        encoder.output = self.video_splitter
        self.encoders['video'] = encoder

    def add_mjpeg_stream(self, config):
        self.mjpeg_config = config
        self.streaming_output = StreamingOutput()
        web_enc = JpegEncoder()
        web_out = FileOutput(self.streaming_output)
        self.encoders['mjpeg'] = (web_enc, web_out)

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

    def start_mjpeg_stream(self):
        self.serve_mjpeg(output=self.streaming_output)

    def serve_mjpeg(self, output):
        address = ('', self.mjpeg_config['port'])
        self.logger.info('Webstream started at http://{}:{}'.format(get_ip(), address[1]))
        StreamingHandler.output = output
        StreamingHandler.cam_name = self.name
        StreamingHandler.resolution = self.frame_size
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()

    def stop(self):
        self.logger.info("Stopping picam")
        self.cam.stop_encoder()
        self.cam.stop()
        self.logger.info("Picam stopped")
