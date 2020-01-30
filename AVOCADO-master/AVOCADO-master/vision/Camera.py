import cv2
import multiprocessing as mp
import numpy as np
import os

import sys
import pyzed.sl as sl
import math
import time

import ObjectDetection
import LaneDetection
import Platooning
import darknet_zed
import Recorder

import select

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

def main():
    X_shape = (360, 640, 3)
    X = mp.RawArray("b", X_shape[0] * X_shape[1] * X_shape[2])
    Y = mp.RawArray("b", X_shape[0] * X_shape[1] * X_shape[2])
    depthX = mp.RawArray("b", X_shape[0] * X_shape[1] * X_shape[2])
    depthY = mp.RawArray("b", X_shape[0] * X_shape[1] * X_shape[2])
    #processes = [mp.Process(target=LaneDetection.main, args=()),
    #        mp.Process(target=ObjectDetection.OD, args=())]
    #processes = [mp.Process(target=LaneDetection.LD, args=(X_shape, X, Y)),
    #        mp.Process(target=ObjectDetection.OD, args=(X_shape, X, Y)),
    #        mp.Process(target=Platooning.Platooning, args=(X_shape, X, Y)),
    #        mp.Process(target=darknet_zed.main, args=(X_shape, X, Y)),
    #        mp.Process(target=Recorder.Recorder, args=(X_shape, X, Y))]
    processes = [mp.Process(name="LaneDetection.py", target=LaneDetection.LD, args=(X_shape, X, Y)),
            mp.Process(name="Platooning.py", target=Platooning.Platooning, args=(X_shape, X, Y)),
            mp.Process(name="darknet_zed.py", target=darknet_zed.main, args=(X_shape, X, Y, depthX, depthY)),
            mp.Process(name="Recorder.py", target=Recorder.Recorder, args=(X_shape, X, Y))]

    for p in processes:
        p.start() #TODO Need everyone to pause while camera starts up

    '''
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    '''
    # Create a ZED camera object
    zed = sl.Camera()

    # Set configuration parameters
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.RESOLUTION_VGA
    init.depth_mode = sl.DEPTH_MODE.DEPTH_MODE_PERFORMANCE
    init.coordinate_units = sl.UNIT.UNIT_METER
    #init.depth_minimum_distance = 0.5 # min depth
    print(init.camera_fps)
    #init.camera_fps = 60

    if len(sys.argv) >= 2 :
        init.svo_input_filename = sys.argv[1]

    # Open the camera
    err = zed.open(init)
    if err != sl.ERROR_CODE.SUCCESS :
        print(repr(err))
        zed.close()
        exit(1)
    zed.set_depth_max_range_value(3) # max depth

    # Set runtime parameters after opening the camera
    runtime = sl.RuntimeParameters()
    runtime.sensing_mode = sl.SENSING_MODE.SENSING_MODE_STANDARD

    # Prepare new image size to retrieve half-resolution images
    image_size = zed.get_resolution()
    new_width = image_size.width #/2
    new_height = image_size.height# /2

    # Declare your sl.Mat matrices
    image_zed = sl.Mat(new_width, new_height, sl.MAT_TYPE.MAT_TYPE_8U_C4)
    depth_image_zed = sl.Mat(new_width, new_height, sl.MAT_TYPE.MAT_TYPE_8U_C4)
    memImgX = np.frombuffer(X, dtype=np.int8).reshape(X_shape)
    memImgY = np.frombuffer(Y, dtype=np.int8).reshape(X_shape)
    memDepthX = np.frombuffer(depthX, dtype=np.int8).reshape(X_shape)
    memDepthY = np.frombuffer(depthY, dtype=np.int8).reshape(X_shape)



    # Open pipes after spinning off processes
    pipeLD = os.open("/tmp/camera_to_LD", os.O_WRONLY) # TODO Error check
    pipeOD = os.open("/tmp/camera_to_OD", os.O_WRONLY) # TODO Error check
    pipePlatooning = os.open("/tmp/camera_to_Platooning", os.O_WRONLY) # TODO Error check
    pipeCamera = os.open("/tmp/camera_to_recorder", os.O_WRONLY) # TODO Error check
    pipeParserToCamera = os.open("/tmp/parser_to_camera", os.O_RDONLY)
    parserToCameraPoll = select.poll()
    parserToCameraPoll.register(pipeParserToCamera, select.POLLIN)

    count = 0
    frame_counter = 0
    print("Starting Camera.py")
    quicks = []
    while True:
        #print("Camera: " + str(frame_counter))
        # do camera reading here
        #ret, img = cap.read()
        quick_t = time.time()
        if parserToCameraPoll.poll(0):
            line = os.read(pipeParserToCamera, 10).decode()
            if line and (line[0] == 'q' or line[0] == 'Q'):
                break
        err = zed.grab(runtime)
        if err == sl.ERROR_CODE.SUCCESS :
            # Retrieve the left image, depth image in the half-resolution
            zed.retrieve_image(image_zed, sl.VIEW.VIEW_LEFT, sl.MEM.MEM_CPU, int(new_width), int(new_height))
            zed.retrieve_image(depth_image_zed, sl.VIEW.VIEW_DEPTH, sl.MEM.MEM_CPU, int(new_width), int(new_height))
            # Retrieve the RGBA point cloud in half resolution
            # To recover data from sl.Mat to use it with opencv, use the get_data() method
            # It returns a numpy array that can be used as a matrix with opencv
            image_ocv = image_zed.get_data()
            depth_image_ocv = depth_image_zed.get_data()
        img = image_ocv[:, :, :3]
        depth = depth_image_ocv[:, :, :3]
        img = cv2.resize(img, (640, 360))
        depth = cv2.resize(depth, (640, 360))
        # TODO GET IMG HERE
        if ((count & 1) == 0):
            np.copyto(memImgX, img.astype(np.int8)) # TODO as uint8?
            np.copyto(memDepthX, depth.astype(np.int8))
        else:
            np.copyto(memImgY, img.astype(np.int8))
            np.copyto(memDepthY, depth.astype(np.int8))
        os.write(pipeLD, (str(count) + "\0").encode())
        os.write(pipeOD, (str(count) + "\0").encode())
        os.write(pipePlatooning, (str(count) + "\0").encode())
        os.write(pipeCamera, (str(count) + "\0").encode())
        #print("Camera: " + str(frame_counter))
        frame_counter += 1
        count = (count + 1) & 1
        quicks.append(time.time() - quick_t)
        #print(1000 * sum(quicks) / len(quicks))

    for p in processes:
        print("SIGTERM: " + p.name)
        p.terminate()
    while True:
        pass # wait to be killed by main



if __name__ == "__main__":
    main()
