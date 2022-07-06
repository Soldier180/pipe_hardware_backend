from videostream import WebcamVideoStream
from flask import Response
from flask import Flask
import threading
import time
import cv2
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

#config stream
import subprocess as sp
cmd = ['ffmpeg',
        '-re',
        '-stream_loop',  '-1',
        '-i', config["VIDEO"]["file_location"],
       '-preset', 'ultrafast',
        '-vcodec', 'mpeg4',
       '-tune', 'zerolatency',
       '-b', '900k',
       '-f',  'h264',
       config["VIDEO"]["stream_address"]]


# cmd = ['ffmpeg',
#         '-f', 'dshow',#'-re',
#         #'-stream_loop',  '-1',
#         '-i', 'video=HD Camera',#config["VIDEO"]["file_location"],
#        '-preset', 'ultrafast',
#         '-vcodec', 'mpeg4',
#        '-tune', 'zerolatency',
#        '-b', '100k',
#        '-f',  'h264',
#        config["VIDEO"]["stream_address"]]
def start_stream():
    sp.run(cmd)

video_stream_th = threading.Thread(target=start_stream, args=())
# video_stream_th.daemon = True
video_stream_th.start()
time.sleep(3)


outputFrame = None
lock = threading.Lock()

app = Flask(__name__)
vs = WebcamVideoStream(src=config["VIDEO"]["stream_address"]).start()
time.sleep(1.0)


def img_processing():
    global vs, outputFrame, lock
    # loop over frames from the video stream
    while True:
        frame = vs.read()
        if not vs.grabbed:
            continue
        # lock
        with lock:
            outputFrame = frame.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')


@app.route("/videostream")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# check to see if this is the main thread of execution
if __name__ == '__main__':

    t = threading.Thread(target=img_processing, args=())
    t.daemon = True
    t.start()
    # start the flask app
    app.run(host=config["WEB_STREAM"]["host"], port=int(config["WEB_STREAM"]["port"]), debug=True, threaded=True, use_reloader=False)
# release the video stream pointer
vs.stop()



# VIDSOURCE="rtsp://username:password@ip-address-of-camera:554/cam/realmonitor?channel=1&subtype=0"
# AUDIO_OPTS="-c:a aac -b:a 160000 -ac 2"
# VIDEO_OPTS="-s 854x480 -c:v libx264 -b:v 800000"
# OUTPUT_HLS="-hls_time 10 -hls_list_size 10 -start_number 1"
# ffmpeg -i video="HD Camera" -y -s 854x480 -c:v libx264 -b:v 800000 -hls_time 10 -hls_list_size 10 -start_number 1 mystream.m3u8