# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import logging
import socketserver
import urllib.parse
from http import server

PAGE = """\
<html>
<head>
<title>Streaming {0}</title>
</head>
<body>
<h1>Streaming {0}</h1>
<img src="stream" width="{1}" height="{2}" />
</body>
</html>
"""


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        from threading import Condition
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    cam_name = 'unknown camera'
    resolution = [640, 480]
    output = None

    def do_GET(self):
        parsed_path = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        path = parsed_path.path
        if path == '/':
            self.send_response(301)
            self.send_header('Location', '/index')
            self.end_headers()
        elif path == '/index':
            width, height = self.resolution
            scale = params.get('scale')
            scale = float(scale[0]) if scale else 1.0
            page_content = PAGE.format(self.cam_name, scale * width, scale * height)
            content = page_content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif path == '/stream':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with self.output.condition:
                        self.output.condition.wait()
                        frame = self.output.frame
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
