import time
import os
import numpy as np
import cv2
import select
import sys

def Platooning(imgShape=None, memImgX=None, memImgY=None):
    PATH = "/tmp/platoon_to_motor"
    imgX8 = np.frombuffer(memImgX, dtype=np.int8).reshape(imgShape)
    imgY8 = np.frombuffer(memImgY, dtype=np.int8).reshape(imgShape)

    lower1 = np.array([0, 175, 60])
    upper1 = np.array([5, 255, 255])
    lower2 = np.array([175, 175, 60])
    upper2 = np.array([180, 255, 255])
    
    pipeFromCamera = os.open("/tmp/camera_to_Platooning", os.O_RDONLY) # TODO Error check
    parserPipe = os.open("/tmp/parser_to_platoon", os.O_RDONLY)
    distPipe = os.open("/tmp/platooning_dist_pipe", os.O_WRONLY)
    motorPipe = os.open("/tmp/platooning_to_motor", os.O_WRONLY)
    velPipe = os.open("/tmp/platooning_vel_pipe", os.O_WRONLY)

    prevHeight = None

    # Filtering
    heightFilter = None
    dHeightFilter = None
    filterLength = 4

    # States (used for turning)
    inTurn = False

    # For polling stdin
    p = select.poll()
    p.register(parserPipe, select.POLLIN)

    platooning = False

    # TODO Manage broken pipes
    print("Starting Platooning.py")
    while True:
        # Blocking read from camera. Waiting on next frame
        imgIndexString = os.read(pipeFromCamera, 10).decode("utf8")
        try:
            imgIndex = int(imgIndexString[0]) # index of frame to read
        except IndexError:
            print("vision/Platooning.py: IndexError: " + str(imgIndexString))
            break
        if p.poll(1):
            line = os.read(parserPipe, 10).decode("utf8")
            if (line[0] == "n" and platooning):
                print("Breaking platoon!")
                platooning = False
                os.write(motorPipe, "n\0".encode())
            elif (line[0] == "p" and not platooning):
                print("Forming platoon!")
                platooning = True
                os.write(motorPipe, "p\0".encode())
        #if False:
        if platooning:
            if (imgIndex & 1 == 0): # if even
                continue
                img = imgX8.astype(np.uint8) # returns copy by default
            else: # if odd
                img = imgY8.astype(np.uint8)
            img = cv2.resize(img, (320, 180))
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
            _, contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
            if (len(contours) > 0):
                c = max(contours, key=cv2.contourArea)
                rect = cv2.minAreaRect(c)
                box = np.int0(cv2.boxPoints(rect))
                pts = np.sort(box[:, 1])

                # For debugging the bounding box
                '''
                box8 = np.int0(box)
                cv2.drawContours(img, [box8], 0, (0, 255, 0), 2)
                cv2.imshow("img", img)
                cv2.waitKey(1)
                '''

                height = abs(((pts[0] + pts[1]) / 2) - ((pts[2] + pts[3]) / 2))
                # Close up saturation
                if (height > 255):
                    height = 255 # saturate height at 255 for a single byte
                # Far away saturation
                '''
                if (height < 50):
                    height = 50
                    dHeight = 0
                if (height < 10):
                    dHeight = 0
                '''
                # dHeight calculation
                if (prevHeight == None):
                    dHeight = 0
                    prevHeight = height
                else:
                    dHeight = prevHeight - height
                    prevHeight = height
                # Check if in turn
    
    
    
                '''
                if (height > 60):
                    pass
                    #inTurn = False
                elif (heightFilter != None and height < heightFilter[0] - 40): #dHeight > 30 and height > 80 and not inTurn):
                    print("IN TURN!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    #inTurn = True
                if inTurn:
                    height = heightFilter[-1]
                    dHeight = dHeightFilter[-1]
                else:
                    # Filtering
                    if (heightFilter == None):
                        heightFilter = [height for i in range(filterLength)]
                        dHeightFilter = [dHeight for i in range(filterLength)]
                    else:
                        heightFilter.pop(0)
                        dHeightFilter.pop(0)
                        heightFilter.append(height)
                        dHeightFilter.append(dHeight)
                        height = np.median(heightFilter)
                        dHeight = np.median(dHeightFilter)
                '''
    
    
    
                if (heightFilter == None):
                    heightFilter = [height for i in range(filterLength)]
                    dHeightFilter = [dHeight for i in range(filterLength)]
                else:
                    heightFilter.pop(0)
                    dHeightFilter.pop(0)
                    heightFilter.append(height)
                    dHeightFilter.append(dHeight)
                    height = np.median(heightFilter)
                    dHeight = np.median(dHeightFilter)
                height = int(height)
                #print("==========================================================")
                #print("From inside platooning: " + str(height))
                #print(str(height) + "    " + str(dHeight))
                height *= 4
                dHeight *= 4
                os.write(distPipe, (str(height) + "\0").encode())
                os.write(velPipe, (str(dHeight) + "\0").encode())
            else:
                #print("From inside platooning: " + str(height))
                os.write(distPipe, ("0\0").encode())
                os.write(velPipe, "0\0".encode())



if __name__ == "__main__":
    main()



