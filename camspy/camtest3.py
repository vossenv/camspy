# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import logging
import socketserver
import time
from http import server
from threading import Condition

import picamera2
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.outputs import FfmpegOutput


PAGE = """\
<html>
<head>
<title>picamera2 MJPEG streaming demo</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
output = StreamingOutput()
picam2.start_recording(JpegEncoder(), FileOutput(output))

try:

    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()

print('xxx')

# picam2 = Picamera2()
# camera_config = picam2.create_preview_configuration()
# picam2.configure(camera_config)
# # picam2.start_preview(Preview.DRM)
# picam2.start()
# time.sleep(2)
# picam2.capture_file("test.jpg")

# with picamera2.Picamera2(resolution='640x480', framerate=24) as camera:

# encoder = H264Encoder(10000000)
#
# with picamera2.Picamera2() as camera:
#     camera_config = camera.create_preview_configuration()
#     camera.configure(camera_config)
#     camera.start()
#     output = StreamingOutput()
#     video_output = FfmpegOutput("video.mp4")
#     camera.start_recording(encoder=encoder, output=output)
#     time.sleep(5)  # Recording duration in seconds
#     camera.stop_recording()
#     print("Recording finished.")
#     camera.stop()

    # #Uncomment the next line to change your Pi's Camera rotation (in degrees)
    # #camera.rotation = 90
    # camera.start_recording(output, format='mjpeg')
    # try:
    #     address = ('', 8000)
    #     server = StreamingServer(address, StreamingHandler)
    #     server.serve_forever()
    # finally:
    #     camera.stop_recording()
