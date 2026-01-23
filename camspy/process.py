import logging

from camspy.camera import Camera  # , PiCamDirect


class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("processor")
        self.camera = Camera.create(self.config['device'])
        processing_config = config['processing']
        self.connector = None
        self.text_scaling = {}
        self.record_video = processing_config['record_video']
        self.recording_directory = processing_config['recording_directory']
        self.send_images = processing_config['send_images']
        self.send_video = processing_config['send_video']
        self.video_filesize = processing_config['video_filesize']
        self.crop = processing_config['crop']
        self.rotation = processing_config['rotation']
        self.image_size = processing_config['image_size']
        self.data_scaling = {
            'video': processing_config['data_bar_video'],
            'web': processing_config['data_bar_web']
        }
        self.target_web_framerate = processing_config['target_web_framerate']
        self.target_video_framerate = processing_config['target_video_framerate']
        self.show_fps = processing_config['show_fps']
        self.vid_pid = processing_config['video_fr_pid']
        self.web_pid = processing_config['web_fr_pid']
        self.log_metrics = self.config['logging']['log_metrics']
        self.ignore_warnings = self.camera.ignore_warnings = self.config['logging']['ignore_warnings']
        self.log_extra_info = self.camera.log_extra_info = self.config['logging']['log_extra_info']
        self.camera.log_metrics = self.log_metrics
        self.camera.capture_image = self.send_images
        self.camera.framerate = processing_config['target_video_framerate']


class StreamProcessor(DataProcessor):
    def __init__(self, config):
        super(StreamProcessor, self).__init__(config)
        self.logger = logging.getLogger("streamer")

    def run(self):
        # self.camera.test_cam()
        self.camera.test_cam()
        # self.camera.connect()
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

