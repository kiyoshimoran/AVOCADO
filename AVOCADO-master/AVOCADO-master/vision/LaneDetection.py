import cv2
import numpy as np
import time
import sys
import getpass
import os
import select

REDUCED_OFFSET = 197


class Filter_Frame:
    def __init__(self, pts, filter_size):
        # Make indices tracker
        self.indices = []
        _ = [-1] * filter_size
        self.indices.append(_)
        _ = [-1] * filter_size
        self.indices.append(_)

        self.ptMaps = {}
        self.size = filter_size
        self.pts = [0, 0]
        self.pts = [np.array(np.zeros(len(pts) * filter_size)).reshape((len(pts), filter_size)),
                    np.array(np.zeros(len(pts) * filter_size)).reshape((len(pts), filter_size))]
        # Make dictionary map from large values to indices
        for i in range(len(pts)):
            self.ptMaps[str(pts[i])] = i

    def add_pt(self, side, row, value):
        index = self.ptMaps[str(row)]
        self.indices[side][index] = (self.indices[side][index] + 1) % self.size
        self.pts[side][index, self.indices[side][index]] = value

    def get_last_pt(self, side, row):
        index = self.ptMaps[str(row)]
        return self.pts[side][index, self.indices[side][index]]

    def get_recent_mean(self, side):
        return np.mean(self.pts[side][:, self.indices[side][0]])

    def __str__(self):
        print(self.pts[0])
        print(self.pts[1])
        return ""
        output = "["
        for pt in self.pts:
            output += str(pt)
            output += ", "
        output += "]"
        return output


def find_edge(bw, search_direction):
    vals = np.where(bw) # get non-zero indices
    if np.size(vals) > 0: # if indices found
        x = vals[-1][-1] # get largest index
        return x
    return 0


def find_lane(bw, search_direction):
    vals = np.where(bw) # get non-zero indices
    if np.size(vals) > 0: # if indices found
        x = vals[-1][-1] # get largest index
        if ((x-30) >= 0 and bw[x-30] == 0):
            return x
    return False


def main():
    LD()

def LD(imgShape=None, memImgX=None, memImgY=None):
    saveVideo = True
    reduceResolution = True
    
    WHITE = 255
    BLACK = 0
    WHITE_PX = (255, 255, 255)
    BLACK_PX = (0, 0, 0)
    RED = (0, 0, 255)
    GREEN = (0, 255, 0)
    BLUE = (255, 0, 0)
    LEFT = 0
    RIGHT = 1
    
    row_delta = 20 # originally 20
    
    if reduceResolution:
        FRAME_WIDTH = 640
        FRAME_HEIGHT = 360
        multiplier = 2
    else:
        FRAME_WIDTH = 1280
        FRAME_HEIGHT = 720
        multiplier = 1

    if (saveVideo):
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("outputLT.avi", fourcc, 30.0, (320, 180))

    if (sys.version[0] != '3'):
        print("ERR: Must use python3!")
        exit(-1)
    inputFile = 1
    if not (memImgX):
        cap = cv2.VideoCapture(inputFile)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        if (not cap):
            print("ERR: Camera initialization failed in lane detection main")
            return False
    else:
        imgX8 = np.frombuffer(memImgX, dtype=np.int8).reshape(imgShape)
        imgY8 = np.frombuffer(memImgY, dtype=np.int8).reshape(imgShape)
    #TODO Make the ROI top and bottom variables of FRAME_HEIGHT
    if reduceResolution:
        roi_pos = [0, FRAME_WIDTH, 250, 300] #[0, 1280, 400, 500]
        OFFSET = REDUCED_OFFSET #200#225
        resolutionMultiplier = 2
    else:
        roi_pos = [0, FRAME_WIDTH, 500, 600] #[0, 1280, 400, 500]
        OFFSET = 450
        resolutionMultiplier = 1
    frame_no = 0
    filter_size = 5
    lane_width = None
    prev_middle_of_road = None
    _ = [i for i in range(roi_pos[2], roi_pos[3], row_delta)]
    new_history = Filter_Frame(_, filter_size)


    prevTime = time.time()
    fout = open("vision/logs/LDlog.txt", "w")
    fout.close()

    delayQueue = []
    pipeFromCamera = os.open("/tmp/camera_to_LD", os.O_RDONLY) # TODO Error check
    lc_read = os.open("/tmp/comm_to_lane_change", os.O_RDONLY) # TODO Error check
    pipe = os.open("/tmp/lane_detection_position", os.O_WRONLY) # TODO Error check
    lane_change_pipe = os.open("/tmp/lane_change", os.O_RDONLY) # TODO Error check
    lc_write = os.open("/tmp/lane_change_to_comm", os.O_WRONLY) # TODO Error check
    recorder_pipe = os.open("/tmp/lane_to_recorder", os.O_WRONLY)
    lanes_to_pp = os.open("/tmp/lanes_to_pp", os.O_WRONLY)
    pp_to_lanes = os.open("/tmp/pp_to_lanes", os.O_RDONLY)
    lane_change_poll = select.poll()
    lane_change_poll.register(lane_change_pipe, select.POLLIN)
    lcCommPoll = select.poll()
    lcCommPoll.register(lc_read, select.POLLIN)

    ppToLanesPoll = select.poll()
    ppToLanesPoll.register(pp_to_lanes, select.POLLIN)

    lane_change = 0
    changing_lanes = False
    ttmp = time.time()
    print("Starting LaneDetection.py")
    ma = 0
    mi = 1
    average = []
    quick_t = time.time()
    quicks = []
    while True:
        send_to_comm = True
        #print(len(quicks) / sum(quicks))
        #print(time.time() - quick_t)
        quick_t = time.time()
        to_pp = []

        #print(frame_no)
        '''
        if (frame_no % 10 == 0):
            print(1 / (time.time() - ttmp))
        '''
        if not memImgX:
            sys.stderr.write("Polled camera\n")
            ret, img = cap.read()
            if (not ret): # return failed
                print("ERR: Failed to read frame in lane detection main")
                break
        else:
            imgIndexString = os.read(pipeFromCamera, 10).decode("utf8")
            imgIndex = int(imgIndexString[0])
            if (imgIndex & 1 == 0):
                img = imgX8.astype(np.uint8)
            else:
                img = imgY8.astype(np.uint8)
        ttmp = time.time()
        if reduceResolution:
            pass
            #img = cv2.resize(img, (640, 360))
        original = np.copy(img)
        img_height, img_width, img_channels = original.shape
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY) # cvt to gray
        gray = cv2.GaussianBlur(gray, (5, 5), 0) # blur to reduce noise
        (thresh, bw) = cv2.threshold(gray, 128, 255, 
                cv2.THRESH_BINARY | cv2.THRESH_OTSU) # make black/white
        #(thresh, bw) = cv2.threshold(gray, 60, 255, # was 175 in capstone
        #        cv2.THRESH_BINARY) # make black/white
        #bw = (255 - bw)        # this inverts image
        if lane_change_poll.poll(0):
            print("From user")
            line = os.read(lane_change_pipe, 10)#.decode("utf8")
        elif lcCommPoll.poll(0):
            line = os.read(lc_read, 10).decode("utf8")
            if line[0] == "g":
                line = [103]
            elif line[1] == "h":
                line = [104]
        elif ppToLanesPoll.poll(0):
            line = os.read(pp_to_lanes, 10).decode("utf8")
            if line[0] == "g":
                print("Turn left!")
                line = [103]
            elif line[0] == "h":
                print("Turn right!")
                line = [104]
            elif line[0] == "G":
                print("Turn left!")
                line = [103]
                send_to_comm = False
            elif line[0] == "H":
                print("Turn right!")
                line = [104]
                send_to_comm = False

        else:
            line = 0
        if line:
            changing_lanes = True
            lane_change_start = time.time()
            if send_to_comm and line[0] == 103: # is g
                print("Sending g")
                lane_change = "l"
                os.write(lc_write, (lane_change + "\0").encode())
            elif send_to_comm and line[0] == 104: # is h
                print("Sending h")
                lane_change = "r"
                os.write(lc_write, (lane_change + "\0").encode())
            OFFSET = 0
        else:
            lane_change = False
        if changing_lanes and time.time() - lane_change_start > 0.25:
            OFFSET = REDUCED_OFFSET #200#225
            changing_lanes = False
        elif changing_lanes:
            cv2.putText(original, "LANE CHANGE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 3)
        if (False):
            sys.stderr.write("OTSU Threshold of: " + str(thresh) + "\n")
            sys.stderr.flush()

        tmp_index = 0
        pts_to_record = []
        pt_to_record = []
        to_pp_tmp = []
        other_lane = []
        for row in range(roi_pos[2], roi_pos[3], row_delta):
            if lane_change:
                print("Changing lanes")
                if lane_change == "l":
                    x = int(max(0, new_history.get_last_pt(LEFT, row) - 40))
                elif lane_change == "r":
                    x = int(min(img_width - 1, new_history.get_last_pt(RIGHT, row) + 40))
            elif (frame_no < 20):
                x = int((roi_pos[0] + roi_pos[1]) / 2)                      # improve this for faster search
            elif changing_lanes:
                x = int(new_history.get_last_pt(LEFT, row) + 20)
            else:
                old_right = int(new_history.get_last_pt(RIGHT, row))
                if old_right < 100:
                    x = max(old_right - 20, 0)
                else:
                    x = int(new_history.get_last_pt(LEFT, row) + 80)
            if (x >= FRAME_WIDTH):
                x = FRAME_WIDTH - 1 # start search from right edge, which means -1


            x = find_edge(bw[row][:x], LEFT)
            #UE = 75
            #if x-UE > 0:
            #    outside = find_lane(bw[row-50][:x-UE], LEFT)
            #else:
            #    outside = False
            #'''
            #print(outside)
            #cv2.circle(original, (300, row-50), 5, (0, 255, 255), 2)
            #'''
            #if outside:
            #    cv2.circle(original, (outside, row-50), 5, (0, 255, 255), 2)
            #    cv2.circle(original, (x-UE, row-50), 5, (255, 255, 0), 2)
            #    #cv2.circle(original, (outside - 30, row-50), 5, (0, 255, 255), 2)
            

            x = int(x)
            if lane_change:
                for i in range(10):
                    new_history.add_pt(LEFT, row, x)

            new_history.add_pt(LEFT, row, x)
            tmp_index += 1
            cv2.circle(original, (x, row), 5, GREEN, 2)
            pt_to_record.append((x, row))
            to_pp_tmp.append((x * multiplier, row * multiplier)) # change if changing resolution
            #if outside:
            #    other_lane.append((outside * multiplier, (row-50) * multiplier))
        #if len(other_lane) > 1:
        #    print("LANE!!!")
        #else:
        #    print("No lane")
        #top = to_pp_tmp[2][0] - to_pp_tmp[0][0]
        #bottom = to_pp_tmp[2][1] - to_pp_tmp[0][1]
        #multiply_by = -50
        #quick_total = int((top / bottom) * multiply_by + to_pp_tmp[0][0])
        #quick_total = int(quick_total / 2)
        #cv2.circle(original, (quick_total, roi_pos[2] - 50), 5, (255, 255, 0), 2)
        #print(to_pp_tmp)
        #print(top)
        #print(bottom)
        #print(multiply_by)
        #print(quick_total)
        to_pp.append(to_pp_tmp)
        pts_to_record.append(pt_to_record)
        pt_to_record = []
        tmp_index = 0
        to_pp_tmp = []
        for row in range(roi_pos[2], roi_pos[3], row_delta):
            if lane_change:
                if lane_change == "l":
                    x = int(max(0, new_history.get_last_pt(LEFT, row) + 40))
                elif lane_change == "r":
                    x = int(min(img_width - 1, new_history.get_last_pt(RIGHT, row) + 40))
            elif (frame_no < 20):
                x = int((roi_pos[0] + roi_pos[1]) / 2)                      # improve this for faster search
            elif changing_lanes:
                x = int(new_history.get_last_pt(RIGHT, row) - 20)
            else:
                #x = int(new_history.get_last_pt(RIGHT, row) - 80)
                old_left = int(new_history.get_last_pt(LEFT, row))
                if old_left > img_width - 100: # has drifted very far to side of frame
                    x = min(old_left + 20, img_width - 1) # take an offset from the previous left lane
                else:
                    x = int(new_history.get_last_pt(RIGHT, row) - 80) # no drift, just take offset from prev right
            if (x < 0):
                x = 0 # start search from left edge
            vals = np.where(bw[row][x:]) # get non-zero indices
            if np.size(vals) > 0: # if indices found
                x += vals[-1][0] # add smallest index to where search started
            else: # x = 0 because (no indices found)
                x = img_width - 1
            x = int(x)
            if lane_change:
                for i in range(10):
                    new_history.add_pt(RIGHT, row, x)

            new_history.add_pt(RIGHT, row, x)
            tmp_index += 1
            cv2.circle(original, (x, row), 5, RED, 2)
            pt_to_record.append((x, row))
            to_pp_tmp.append((x * multiplier, row * multiplier)) # change if changing resolution

        to_pp.append(to_pp_tmp)
        pts_to_record.append(pt_to_record)
        pt_to_record = []

        left_pt = new_history.get_last_pt(LEFT, roi_pos[2])
        right_pt = new_history.get_last_pt(RIGHT, roi_pos[2])
        left_sum = 0
        right_sum = 0
        count = 0
        for row in range(roi_pos[2], roi_pos[3], row_delta):
            left_sum += new_history.get_last_pt(LEFT, row)
            right_sum += new_history.get_last_pt(RIGHT, row)
            count += 1
        #sys.stderr.write(str((right_sum - left_sum)) + "\n")

        # Correct for losing lanes
        if (lane_width == None): # first frame
            # set lane width
            lane_width = int((right_sum - left_sum) / (count))
            middle_pt = int((left_sum + right_sum) / (count * 2))
            #sys.stderr.write("LANE WIDTH IS: " + str(lane_width) + "\n")
            #cv2.putText(original, "LANE WIDTH IS: " + str(lane_width), (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN)
        elif (new_history.get_recent_mean(LEFT) <= 0 and new_history.get_recent_mean(RIGHT) >= FRAME_WIDTH - 1): # lost both lanes
            middle_pt = int((right_sum / count) / 2)
        elif (new_history.get_recent_mean(LEFT) <= 0): # lost left lane
            #middle_pt = int((right_sum / count) - (lane_width / 2) - OFFSET) # go left of right lane
            middle_pt = int((right_sum / count) - OFFSET)
            #cv2.putText(original, "LOST LEFT LANE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 4)
        elif (new_history.get_recent_mean(RIGHT) >= FRAME_WIDTH - 1): # lost right lane
            #middle_pt = int((left_sum / count) + (lane_width / 2) + OFFSET) # go right of left lane
            middle_pt = int((right_sum / count) + OFFSET)
            #cv2.putText(original, "LOST RIGHT LANE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 4)
        elif (int((right_sum - left_sum) / (count)) < 150): # if width less than 200 but both found
            middle_pt = prev_middle_of_road
            #cv2.putText(original, "TOO NARROW", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 2)
            #sys.stderr.write("WOAHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH\n")
        else:
            middle_pt = int((left_sum + right_sum) / (count * 2))
            #cv2.putText(original, "LOST NO LANE", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 4)
        prev_middle_of_road = middle_pt


        #middle_pt = int((left_pt + right_pt) / 2)
        #sys.stderr.write(str(new_history.get_recent_mean(LEFT)) + "   " + str(new_history.get_recent_mean(RIGHT)) + "\n")
        cv2.putText(original, str(middle_pt), (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, GREEN, 2)
        #sys.stderr.write("---\n")
        #sys.stderr.write("LD: " + str(middle_pt) + "\n")
        pt_to_record = []
        cv2.circle(original, (middle_pt, roi_pos[2]), 5, BLUE, 2)
        pt_to_record.append((middle_pt, roi_pos[2]))
        pts_to_record.append(pt_to_record)

        os.write(recorder_pipe, (str(pts_to_record) + "|\0").encode())

        timeDelta = time.time() - prevTime
        prevTime = time.time()
        fout = open("vision/logs/LDlog.txt", "a")
        fout.write(str(timeDelta) + "\n")
        fout.close()


        middle_pt_output = middle_pt

        middle_pt_output *= resolutionMultiplier
        os.write(pipe, (str(middle_pt_output) + "\0").encode())
        to_pp.insert(0, [middle_pt_output])
        os.write(lanes_to_pp, (str(to_pp) + "\0|").encode())
        '''
        fout = open("log.txt", "a")
        fout.write(str(middle_pt_output) + "\n")
        fout.close()
        '''


        #cv2.rectangle(original, (roi_pos[0], roi_pos[2]), (roi_pos[1], roi_pos[3]), RED, 2)
        #original = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
        #cv2.imshow("frame", original)
        #cv2.imshow("frame", original)
        #cv2.imshow("bw", bw)
        #cv2.waitKey(1)
        '''
        '''
        if (saveVideo):
            #original = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR) # cvt to gray
            original = cv2.resize(original, (320, 180))
            out.write(original)
        if (cv2.waitKey(1) & 0xFF == ord('q')): # slow frames, quit on 'q'
            break
        frame_no += 1
        quicks.append(time.time() - quick_t)
        #print(sum(quicks) / len(quicks))
    if (saveVideo):
        out.release()
    cv2.destroyAllWindows() # close all windows


if __name__=="__main__":
    main()
