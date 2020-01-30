
import cv2
import numpy as np
import time
import sys
import getpass
import os
import select
import re

RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)

def isInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def parseLanePoints(pts):
    foo = re.split("[ ,()]", pts)
    vals = [int(val) for val in foo if isInt(val)]
    index = 0
    length = len(vals)
    output = []
    if length % 2 != 0:
        return output
    while index < length:
        output.append((vals[index], vals[index+1]))
        index += 2
    return output

def parseObjectPoints(pts):
    foo = re.split("[ ,()]", pts)
    vals = [int(val) for val in foo if val.isdigit()]
    index = 0
    length = len(vals)
    output = []
    if length % 4 != 0:
        return output
    while index < length:
        x = vals[index]
        y = vals[index+1]
        w = vals[index+2]
        h = vals[index+3]
        output.append([(x, y), (x+w, y+h)])
        index += 4
    return output


def Recorder(imgShape=None, memImgX=None, memImgY=None):
    print("Starting Recorder.py")
    saveVideo = True
    reduceResolution = True
    
    if reduceResolution:
        FRAME_WIDTH = 640
        FRAME_HEIGHT = 360
    else:
        FRAME_WIDTH = 1280
        FRAME_HEIGHT = 720

    if (saveVideo):
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("output.avi", fourcc, 30.0, (320, 180))

    if (sys.version[0] != '3'):
        print("ERR: Must use python3!")
        exit(-1)

    imgX8 = np.frombuffer(memImgX, dtype=np.int8).reshape(imgShape)
    imgY8 = np.frombuffer(memImgY, dtype=np.int8).reshape(imgShape)

    # Make pipes here
    #char lane_to_recorder[] = "/tmp/lane_to_recorder";
    #char object_to_recorder[] = "/tmp/object_to_recorder";
    #char platooning_to_recorder[] = "/tmp/platooning_to_recorder";
    camera_pipe = os.open("/tmp/camera_to_recorder", os.O_RDONLY)

    lane_pipe = os.open("/tmp/lane_to_recorder", os.O_RDONLY)
    lane_poll = select.poll()
    lane_poll.register(lane_pipe, select.POLLIN)

    #object_pipe = os.open("/tmp/object_to_recorder", os.O_RDONLY)
    #object_poll = select.poll()
    #object_poll.register(object_pipe, select.POLLIN)

    '''
    platooning_pipe = os.open("/tmp/platooning_to_recorder", os.O_RDONLY)
    platooning_poll = select.poll()
    platooning_poll.register(platooning_poll, select.POLLIN)
    '''

    frame_counter = 0
    while True:
        imgIndexString = os.read(camera_pipe, 10).decode("utf8")
        imgIndex = int(imgIndexString[0])
        if (imgIndex & 1 == 1):
            img = imgX8.astype(np.uint8)
        else:
            img = imgY8.astype(np.uint8)

        if reduceResolution:
            pass
            #img = cv2.resize(img, (640, 360))


        # Draw lane points
        if lane_poll.poll(0):
            #print(frame_counter)
            #frame_counter += 1
            try:
                line = os.read(lane_pipe, 100).decode("utf8").split("|")[-2].split("]")
            except IndexError:
                print("vision/Recorder.py: IndexError: " + str(lane_pipe))
                continue
            '''
            '''
            #left_pts = parseLanePoints(line[0])
            #right_pts = parseLanePoints(line[1])
            #middle_pts = parseLanePoints(line[2])
            #for pt in left_pts:
            #    cv2.circle(img, pt, 5, GREEN, 2)
            #for pt in right_pts:
            #    cv2.circle(img, pt, 5, RED, 2)
            #for pt in middle_pts:
            #    cv2.circle(img, pt, 5, BLUE, 2)

        img = cv2.resize(img, (320, 180))

        #if object_poll.poll(0): # TODO Check if issue that blocks for object points
        #    line = os.read(object_pipe, 100).decode("utf8").split("|")[-2].split("]")
            #print(line)
        #    rects = parseObjectPoints(line[0])
        #    for rect in rects:
        #        cv2.rectangle(img, rect[0], rect[1], GREEN, 2)


        #cv2.imshow("img", img)
        #cv2.waitKey(1)
        if (saveVideo):
            out.write(img)

    if (saveVideo):
        out.release()
    cv2.destroyAllWindows() # close all windows
