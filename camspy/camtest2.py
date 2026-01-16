from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput
import time
picam2 = Picamera2()
video_config = picam2.create_video_configuration()
picam2.configure(video_config)
# encoder = H264Encoder(repeat=True, iperiod=15)
# # encoder = H264Encoder()
# output1 = FfmpegOutput("-f mpegts udp://<ip-address>:12345")
# stream_output = FfmpegOutput("-f rtsp -rtsp_transport udp rtsp://192.168.50.73:8554/stream")
output1 = FfmpegOutput("-f mpegts udp://<ip-address>:12345")

encoder = H264Encoder(10000000) # Bitrate in bits/sec
output2 = FfmpegOutput("my_audio_video.mp4")

# output2 = FileOutput()
# outputff = FfmpegOutput("video2.mp4")
encoder.output = [output1, output2]
# # Start streaming to the network.
picam2.start_encoder(encoder)
picam2.start()
print("Recording and streaming started for 20 seconds...")

# Let it run for a duration
try:
    time.sleep(10)
finally:
    # Stop recording/streaming and the camera
    picam2.stop_encoder()
    picam2.stop()
    print("Stopped.")
# The file is closed, but carry on streaming to the network.
# time.sleep(9999999)


# Start recording (adds audio if microphone is present)
# picam2.start_recording(encoder, output) # audio=True for sound
# time.sleep(10) # Record for 10 seconds
# picam2.stop_recording()

print("Audio/Video recording finished.")