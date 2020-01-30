import time
import os
import numpy as np
import cv2

def main():
    cap = None
    OD(cap)

def sharedChild(imgShape, imgBuffer, imgIndex):
    cap = SharedCamera.SharedCamera(imgShape, imgBuffer, imgIndex)
    OD(cap)

def OD(imgShape=None, memImgX=None, memImgY=None):
    PATH = "/tmp/object_detection_to_motor"
    imgX8 = np.frombuffer(memImgX, dtype=np.int8).reshape(imgShape)
    imgY8 = np.frombuffer(memImgY, dtype=np.int8).reshape(imgShape)

    #lower1 = np.array([0, 110, 60])
    #upper1 = np.array([7, 255, 255])
    #lower2 = np.array([173, 110, 60])
    #upper2 = np.array([180, 255, 255])
    lower1 = np.array([0, 50, 100])
    upper1 = np.array([10, 255, 225])
    lower2 = np.array([178, 50, 100])
    upper2 = np.array([180, 255, 225])

    yellowLower = np.array([15, 50, 130])
    yellowUpper = np.array([40, 240, 255])
    lightBlueLower = np.array([90, 100, 90])
    lightBlueUpper = np.array([150, 220, 220])
    
    pipeFromCamera = os.open("/tmp/camera_to_OD", os.O_RDONLY) # TODO Error check
    pipeMotor = os.open("/tmp/object_detection_to_motor", os.O_WRONLY)
    recorder_pipe = os.open("/tmp/object_to_recorder", os.O_WRONLY)

    state = "d"
    passedObject = False
    
    # TODO Manage broken pipes
    print("Starting ObjectDetection.py")
    while True:
        to_recorder = []

        imgIndexString = os.read(pipeFromCamera, 10).decode("utf8")
        imgIndex = int(imgIndexString[0])
        if (imgIndex & 1 == 0): # if even
            img = imgX8.astype(np.uint8) # returns copy by default
        else: # if odd
            img = imgY8.astype(np.uint8)
        img = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        maskLightBlue = cv2.inRange(hsv, lightBlueLower, lightBlueUpper)
        maskYellow = cv2.inRange(hsv, yellowLower, yellowUpper)
        mask = cv2.bitwise_or(mask1, mask2)
        _, contours, hierarchy = cv2.findContours(maskYellow, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        if (len(contours) > 0):
            c = max(contours, key=cv2.contourArea)
            a = cv2.contourArea(c)
            p = cv2.arcLength(c, True)
            '''
            if (cv2.contourArea(c) > 1000 and (p ** 2) / a < 18):
                os.write(pipeMotor, ("s" + "\0").encode())
                print("yellow area: " + str(cv2.contourArea(c)))
                print("yellow shape: " + str((p ** 2) / a))
            '''
        _, contours, hierarchy = cv2.findContours(maskLightBlue, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        if (len(contours) > 0):
            c = max(contours, key=cv2.contourArea)
            a = cv2.contourArea(c)
            p = cv2.arcLength(c, True)
            '''
            if (cv2.contourArea(c) > 1500 and (p ** 2) / a < 16):
                os.write(pipeMotor, ("l" + "\0").encode())
                print("blue area: " + str(cv2.contourArea(c)))
                print("blue shape: " + str((p ** 2) / a))
            '''
        _, contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        #cv2.imshow("mask", mask)
        #cv2.waitKey(1)
        shouldBrake = False
        if (len(contours) > 0):
            contours = list(filter((lambda x: cv2.contourArea(x) > 300), contours))
            for c in contours:
                a = cv2.contourArea(c)
                p = cv2.arcLength(c, True)
                if ((p ** 2) / a < 30):
                    #print(cv2.contourArea(c))
                    #print((p ** 2) / a)
                    rect = cv2.boundingRect(c)
                    to_recorder.append(rect)
                    state = "b"
                    t = time.time()
        if (state == "d"):
            if shouldBrake:
                os.write(pipeMotor, ("b" + "\0").encode())
                passedObject = False
        elif (state == "b"): # TODO Fix logic to not stop twice
            if (time.time() - t > 6):
                state = "d"
            elif (time.time() - t > 3 and not passedObject):
                os.write(pipeMotor, ("d" + "\0").encode())
                passedObject = True

        if to_recorder:
            os.write(recorder_pipe, (str(to_recorder) + "|\0").encode())

if __name__ == "__main__":
    main()
