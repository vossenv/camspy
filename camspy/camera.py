import logging
import time
from collections import deque

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.outputs import PyavOutput, SplittableOutput

from camspy.model import VideoFile
from camspy.stream import StreamingHandler, StreamingServer, StreamingOutput
from camspy.utils import MultiCounter, start_thread


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
        self.cam_rotate = config['cam_rotate']
        self.codec = config['codec'] if self.camera_type == "picam-direct" else "avi"
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

    def add_video_output(self):
        pass


class PiCam(Camera):

    def __init__(self, config):
        super(PiCam, self).__init__(config)
        self.cam = None
        self.output = []
        self.encoder = H264Encoder(3000000)
        self.encoder.output = []
        self.video_stream = None

    def connect(self):
        self.logger.info("Connecting to picamera")
        for i in range(self.init_retry):
            try:
                self.logger.info("Attempt: {}".format(i))
                self.cam = Picamera2()
                # config = self.cam.create_video_configuration(main={"size": (640, 480)})
                config = self.cam.create_video_configuration(main={"size": (1200, 1200)})
                self.cam.configure(config)
                time.sleep(self.init_delay)
                return
            except Exception as e:
                self.logger.error("Failed to connect to camera: {}: {}".format(type(e), e))
                time.sleep(self.init_delay)
                if i == self.init_retry - 1:
                    raise

    def start(self):
        self.logger.info("Starting picam")
        self.video_stream = VideoFile(filename_prefix='testcam', log_metrics=True)
        f = self.video_stream.get_filename()
        self.cam.start_encoder(self.encoder, output=f)
        self.cam.start()

        # print("Recording and streaming started for 10 seconds...")
        # try:
        #     time.sleep(10)
        # finally:
        #     self.stop()
        #     print("Audio/Video recording finished.")

    def add_video_output(self):
        pass

    def test_cam_stream(self):
        try:
            address = ('', 8000)
            self.connect()
            output = StreamingOutput()
            self.cam.start_recording(JpegEncoder(), FileOutput(output))
            StreamingHandler.output = output
            server = StreamingServer(address, StreamingHandler)
            server.serve_forever()
            while True:
                print('slp')
                time.sleep(5)
        finally:
            self.cam.stop()

    def serve_test(self, output):
        address = ('', 8000)
        self.logger.info('Webstream started at 8000')
        StreamingHandler.output = output
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()

    def test_cam(self):
        dir = 'video'
        filestream = VideoFile(filename_prefix='testcam', log_metrics=True, directory=dir)
        filestream.delete_all()

        self.video_stream = filestream
        filename = filestream.output_filename
        encoder1 = H264Encoder(3000000)
        pyav = PyavOutput(filename)
        splitter = SplittableOutput(output=pyav)
        encoder1.output = splitter

        stream_out = StreamingOutput()
        web_enc = JpegEncoder()
        web_out = FileOutput(stream_out)

        self.connect()
        self.cam.start_encoder(web_enc, web_out)
        self.cam.start_encoder(encoder1)
        self.cam.start()

        start_thread(self.serve_test, output=stream_out)

        self.logger.info("Recording started...")
        try:
            while True:
                time.sleep(5)
                if filestream.should_start_new_file():
                    self.logger.debug("Max size exceeded ({})".format(filestream.disk_size))
                    filename = filestream.new_file()
                    self.logger.debug("Start new file: {}".format(filename))
                    self.logger.info("File count: {}".format(filestream.file_count))
                    splitter.split_output(PyavOutput(filename), wait_for_keyframe=True)
        finally:
            self.cam.stop_encoder()
            self.cam.stop()
            print("Stopped.")

    def stop(self):
        self.logger.info("Stopping picam")
        self.cam.stop_encoder()
        self.cam.stop()
        self.logger.info("Picam stopped")

