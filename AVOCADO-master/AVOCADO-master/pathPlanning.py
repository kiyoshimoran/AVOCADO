import os
import numpy
import sys
import re
import select
import time

import cv2

VALID_LABELS = ["person"]

def in_triangle(leftlane, rtlane, obj):
    left = obj[0]
    right = obj[2]
    try:
        if (((leftlane < left) and (left < rtlane)) or # left pt in lane
            ((leftlane < right) and (rtlane > right)) or # right pt in lane
            ((leftlane < left) and (rtlane > right)) or # both pts in lane
            ((leftlane > left) and (rtlane < right))): # spans lane
                #print("points %s %s in lane" %(left, right))
                return True
       # else:
            #print("not in triangle")
    except TypeError:
        print(left, right, leftlane, rtlane)
    return False


def isInt(x):
    try: 
        int(x)
        return True
    except ValueError:
        return False


#if blocked is true offset should be zero
def in_lanes(leftlane, rtlane, obj):
    blocked = False
    left = obj[0]
    right = obj[2]
    try:
        #print(rtlane, left)
        if leftlane < left and rtlane > left:
            print("FOUND SOMETHING!")
            blocked = True
        elif leftlane < right and rtlane > right: 
            print("FOUND SOMETHING!")
            blocked = True
        elif (leftlane < left and rtlane > right) or (leftlane > left and rtlane < right):
            print("FOUND SOMETHING!")
            blocked = True
       # else:
            #print("not in triangle")
    except TypeError:
        print(left, right, leftlane, rtlane)
    return blocked
    

def interpolate(p1, p2, y3):
    top = p2[0] - p1[0]
    bot = p2[1] - p1[1]
    if bot == 0:
        return (p1[0], y3)
    diff = y3 - p1[1]
    return (int(top / bot * diff + p1[0]), y3)

def parse_lanes(lanes):
    lanes = [val for val in lanes if "[" in val]
    points = []
    mid = left = right = other = 0
    mid_pt = lanes.pop(0)
    mid = int(mid_pt.replace("[", ""))
    points.append(mid)
    for lane in lanes:
        lane = re.split('[(), ]', lane)
        lane = [int(val) for val in lane if isInt(val)]
        points.append(lane)
        continue
        lane = lane[::2]
        pt = int(sum(lane) / len(lane))
        points.append(pt)
    return points

def try_convert_int(i):
    if isInt(i):
        return int(i)
    return i


def parse_objects(objects):
    objects = objects.split(")")
    output = []
    stops = []
    for obj in objects:
        obj = re.split('[\[\]\'(), ]', obj)
        if len(obj) < 6:
            continue
        obj = [try_convert_int(val) for val in obj if val]
        obj = obj[:6]
        try:
            label = obj[5]
        except IndexError:
            continue
        if len(obj) == 6:
            if label == "stop":
                stops.append(obj)
            elif label in VALID_LABELS:
                output.append(obj)
    return output, stops

def partially_in_lane(left, right, x1, x2):
    try:
        if ((left < x1 and x1 < right) or (left < x2 and x2 < right)):
            return True
    except TypeError:
        pass
    return False

def blocking_entire_lane(left, right, x1, x2):
    try:
        if ((x1 < left and left < x2) and (x1 < right and right < x2)):
            return True
    except TypeError:
        pass
    return False

def entirely_in_lane(left, right, x1, x2):
    #print(str(left) + " " + str(right) + " " + str(x1) + " " + str(x2))
    try:
        if ((left < x1 and x1 < right) and (left < x2 and x2 < right)):
            return True
    except TypeError:
        pass
    return False

def road_block(lanes, objects):
    '''
            topleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 0)
            bottomleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 360)
            topright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 0)
            bottomright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 360)
    '''
    '''
    middle = lanes[0]
    left = middle - 75 #lanes[1]
    right = middle + 75 #lanes[2]
    left_lane = lanes[1]
    right_lane = lanes[2]
    width = right - left
    half = width / 2
    '''
    for obj in objects:
        distance = obj[4]
        if distance < 75: # distances are flipped (read from bw depth map)
            continue
       
        x1 = obj[0]
        y1 = obj[1]
        x2 = obj[2]
        y2 = obj[3]
        bottom = y2
        #left_pt = interpolate((left_lane[0], left_lane[1]), (left_lane[2], left_lane[3]), bottom)[0]
        #right_pt = interpolate((right_lane[0], right_lane[1]), (right_lane[2], right_lane[3]), bottom)[0]
        
        try:
            left = lanes[1]
            right = lanes[2]
        except IndexError:
            print("EXCEPTION---------------------------- lanes: " + str(lanes))
            continue
        leftlane = interpolate((left[2], left[3]), (left[4], left[5]), obj[3])[0]
        rightlane = interpolate((right[2], right[3]), (right[4], right[5]), obj[3])[0]
        if in_triangle(leftlane, rightlane, obj):
            print(distance)
            return True
        
        try:
            x1 = int(x1)
            x2 = int(x2)
        except ValueError:
            continue
        '''
        try:
            if (left_pt < x1 and x1 < right_pt) or (left_pt < x2 and x2 < right_pt):
                print("Object detected!")
                return True
        except TypeError:
            continue
        '''
        
        '''
        if blocking_entire_lane(left, right, x1, x2):
            print("Complete roadblock!")
            return True
        elif partially_in_lane(left, right, x1, x2): 
            print("Partial roadblock!")
            return True
        elif entirely_in_lane(left, right, x1, x2):
            print("Entirely in lane!")
            return True
        '''
    return False
    return None

    print(lanes)
    print(objects)
    #for obj in objects:
    #    if (lanes[0] < obj[0] and obj[0] < lanes[1]) or (lanes[0] < obj[2] and obj[2] < lanes[1]) and obj[4] < 0.5:
    #        return 'g'
    return 'n'


#def road_block(lanes, objects, in_right):
#    '''
#            topleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 0)
#            bottomleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 360)
#            topright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 0)
#            bottomright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 360)
#    middle = lanes[0]
#    '''
#    dist =  0
#    mine = adj = blocked = False
#    for obj in objects:
#        distance = obj[4]
#        if distance < 75: # distances are flipped (read from bw depth map)
#            continue
#        try:
#            left = lanes[1]
#            right = lanes[2]
#        except IndexError:
#            print("EXCEPTION---------------------------- lanes: " + str(lanes))
#            continue
#        leftlane = interpolate((left[2], left[3]), (left[4], left[5]), obj[3])[0]
#        rightlane = interpolate((right[2], right[3]), (right[4], right[5]), obj[3])[0]
#        blocked = in_lanes(leftlane, rightlane, obj)
#        if blocked:
#            mine = True
#        '''
#        else:
#            if in_right:
#                blocked = in_lanes(leftlane - 400, leftlane - 10, obj)
#                if blocked: # and distance > 90: 
#                    adj = True
#                    dist = distance
#            else:
#                blocked = in_lanes(rightlane + 10, rightlane + 400, obj)
#                print(obj[0], (rightlane + 400), blocked, distance)
#                if blocked: # and distance > 90: 
#                    adj = True
#                    dist = distance
#        '''
#        #if adj:
#        #    print("object detected in adjacent lane")
#    return mine, dist
#
#    print(lanes)
#    print(objects)
#    #for obj in objects:
#    #    if (lanes[0] < obj[0] and obj[0] < lanes[1]) or (lanes[0] < obj[2] and obj[2] < lanes[1]) and obj[4] < 0.5:
#    #        return 'g'
#    return 'n'

def main():
    saveVideo = True
    if (saveVideo):
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("outputPP.avi", fourcc, 30.0, (320, 180))

    #pipeMotor = os.open("/tmp/object_detection_to_motor", os.O_WRONLY) # Maybe we want this...?
    lanes_pipe = os.open("/tmp/lanes_to_pp", os.O_RDONLY)
    objects_pipe = os.open("/tmp/objects_to_pp", os.O_RDONLY)
    pp_to_LD_controller = os.open("/tmp/pp_to_LD_controller", os.O_WRONLY)
    if pp_to_LD_controller < 0:
        print("pp pipe didnt open\n\n\n")
    pp_to_lanes = os.open("/tmp/pp_to_lanes", os.O_WRONLY)
    pp_to_motor = os.open("/tmp/pp_to_motor", os.O_WRONLY)
    lanes_poll = select.poll()
    lanes_poll.register(lanes_pipe, select.POLLIN)
    objects_poll = select.poll()
    objects_poll.register(objects_pipe, select.POLLIN)

    lanes = None
    objects = None
    stops = None
    print("Starting pathPlanning.py")
    in_right = True
    curr_dodging = False
    t_stop = False
    tdodge = 0
    last_stop = time.time()
    STOP_DURATION = 3
    while True:
        # Get the object stuff
        img = numpy.zeros((360, 640, 3), numpy.uint8)
        if objects_poll.poll(0.5):
            object_data = os.read(objects_pipe, 2048).decode()
            objects, stops = parse_objects(object_data)
        else:
            objects = False
        # Get the lane stuff
        continue
        lane_pts = os.read(lanes_pipe, 2048).decode().split("|")
        if stops and time.time() - last_stop > 6:
            for stop in stops:
                dist = stop[4]
                if dist > 25:
                    os.write(pp_to_motor, ("b\0").encode())
                    t_stop = time.time()
                    last_stop = t_stop
                    break
        if t_stop:
            if time.time() - t_stop < STOP_DURATION:
                continue
            os.write(pp_to_motor, ("d\0").encode())
            t_stop = False
        if len(lane_pts) > 1:
            lane_pts = lane_pts[-2]
        if objects: # only parse if objects found
            try:
                lane_pts = lane_pts.split("]")
            except AttributeError:
                continue
            lanes = parse_lanes(lane_pts)
            
            left = lanes[1]
            right = lanes[2]
            #print(lanes)
            #print(left)
            #def interpolate(p1, p2, x3):
            
            topleft = interpolate((left[0]//2-3, left[1]//2), (left[2]//2, left[3]//2), 0)
            bottomleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 360)
            topright = interpolate((right[0]//2+3, right[1]//2), (right[2]//2, right[3]//2), 0)
            bottomright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 360)
            
            #print(topleft)
            cv2.line(img, topleft, bottomleft, (0, 255, 0), 3)
            cv2.line(img, topright, bottomright, (0, 255, 0), 3)
            cv2.line(img, (left[0]//2, left[1]//2), (left[2]//2, left[3]//2), (0, 0, 255), 3)
            cv2.line(img, (right[0]//2, right[1]//2), (right[2]//2, right[3]//2), (0, 0, 255), 3)
            for obj in objects:
                try:
                    cv2.rectangle(img, (obj[0]//2, obj[1]//2), (obj[2]//2, obj[3]//2), (255, 0, 0), 3)
                    #print(obj)
                except:
                    pass
            '''
            for pt in left:
                #cv2.line(img, pt[0], pt[1], (0, 255, 0), 3)
                #print(pt)
                pass
            '''
            cmd = road_block(lanes, objects)
            cv2.circle(img, (180, 320), 5, (0, 255, 255), 2)
            if not curr_dodging and cmd:
                if in_right:
                    #os.write(pp_to_motor, ("b\0").encode())
                    #os.write(pp_to_lanes, ("g" + "\0").encode())
                    pass
                else:
                    #os.write(pp_to_motor, ("b\0").encode())
                    #os.write(pp_to_lanes, ("h" + "\0").encode())
                    pass
                in_right = not in_right
                print (in_right)
                curr_dodging = True
                tdodge = time.time()
            elif curr_dodging and time.time() - tdodge > 0.5:
                curr_dodging = False
            ##if objects: # determine if objects are in the roadway
            #mine, dist = road_block(lanes, objects, in_right)
            ##mine, adj, dist, offset = road_block(lanes, objects, False)
            #print(mine, adj)
            #if mine and adj and dist > 100:
            #    os.write(pp_to_motor, ("b\0").encode()) # Stop for object
            #    print(dist)
            #    print("both lanes blocked.... Braking")
            #if not curr_dodging and mine:
            #    '''
            #    if adj and dist > 100:
            #        os.write(pp_to_motor, ("b\0").encode()) # Stop for object
            #        print(dist)
            #        print("both lanes blocked.... Braking")
            #        '''
            #    if in_right:
            #        #os.write(pp_to_motor, ("b\0").encode()) # Stop for object
            #        os.write(pp_to_lanes, ("g" + "\0").encode()) # Turn for object
            #        in_right = not in_right
            #        print (in_right)
            #        curr_dodging = True
            #        tdodge = time.time()
            #        print("in right lane, left empty")
            #    else:
            #        #os.write(pp_to_motor, ("b\0").encode())
            #        os.write(pp_to_lanes, ("h" + "\0").encode())
            #        print("in left lane, right empty")
            #        in_right = not in_right
            #        print (in_right)
            #        curr_dodging = True
            #        tdodge = time.time()
            #elif curr_dodging and time.time() - tdodge > 1:
            #    curr_dodging = False
        #cv2.imshow("img", img)
        #cv2.waitKey(1)
        if (saveVideo):
            #original = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR) # cvt to gray
            img = cv2.resize(img, (320, 180))
            out.write(img)

        continue 
        if cmd != 'n':
            os.write(lane_change_pipe, cmd)

if __name__=="__main__":
    main()
