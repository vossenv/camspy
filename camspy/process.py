import logging
import time

from camspy.camera import Camera  # , PiCamDirect
from camspy.model import SFTPConnector, VideoFileHandler
from camspy.utils import start_thread


class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("processor")
        self.camera = Camera.create(self.config['device'])
        processing_config = config['processing']
        self.record_video = processing_config['record_video']
        self.send_video = processing_config['send_video']
        self.mjpeg_stream = processing_config['mjpeg_stream']
        self.video_config = config['recording']
        if self.record_video or self.send_video:
            video_config = self.config['recording']
            self.video_handler = VideoFileHandler(**video_config)

class StreamProcessor(DataProcessor):
    def __init__(self, config):
        super(StreamProcessor, self).__init__(config)
        self.logger = logging.getLogger("streamer")

    def run(self):
        try:
            if self.record_video:
                self.camera.add_video_output(self.config, self.video_handler)
            if self.send_video:
                self.video_handler.add_sftp(SFTPConnector(self.config['sftp']))
                start_thread(self.video_handler.monitor_and_send)
            if self.mjpeg_stream:
                self.camera.add_mjpeg_stream()
            self.camera.start()

            while True:
                time.sleep(3)
        finally:
            try:
                self.camera.stop()
            except:
                pass

        # if self.record_video:
        #     self.camera.add_video_output()
        #
        # # self.camera.connect()
        # self.camera.start()

        # print('banana')

        # while True:
        #     if self.record_video:
        #         time.sleep(5)
        #         self.camera.check_new_file()
        #         self.camera.stop()
        #
        # self.camera.stop()

        #     try:
        #     address = ('', 8000)
        #     StreamingHandler.output = self.camera.output
        #     server = StreamingServer(address, StreamingHandler)
        #     server.serve_forever()
        # finally:
        #     self.camera.stop()

        return
        # while True:
        #     try:
        #         image = self.processor.camera.read_next_frame()
        #         if image is not None:
        #             im.show(self.processor.apply_stream_transforms(image))
        #     except (ImageReadException, ArducamException) as e:
        #         self.logger.warning("Bad image read: {}".format(e))
