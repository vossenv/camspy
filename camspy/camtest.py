from imutils.video import WebcamVideoStream
import cv2
import time

# 1. Start the threaded video stream
vs = WebcamVideoStream(src=0).start() # src=0 for default webcam

# Allow camera to warm up
time.sleep(2.0)

# 2. Loop to capture and display frames
while True:
    frame = vs.read() # Read the next frame

    # 3. Display the frame
    cv2.imshow("Webcam Feed (Press 'q' to quit)", frame)

    # 4. Check for 'q' key press to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 5. Stop the stream and close windows
vs.stop()
cv2.destroyAllWindows()