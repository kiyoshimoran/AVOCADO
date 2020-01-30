#!python3
"""
Python 3 wrapper for identifying objects in images

Requires DLL compilation

Original *nix 2.7: https://github.com/pjreddie/darknet/blob/0f110834f4e18b30d5f101bf8f1724c34b7b83db/python/darknet.py
Windows Python 2.7 version: https://github.com/AlexeyAB/darknet/blob/fc496d52bf22a0bb257300d3c79be9cd80e722cb/build/darknet/x64/darknet.py

@author: Philip Kahn, Aymeric Dujardin
@date: 20180911
"""
# pylint: disable=R, W0401, W0614, W0703
import cv2
import pyzed.sl as sl
from ctypes import *
import math
import random
import os
import numpy as np
import statistics
import sys
import getopt
from random import randint
import re
import time


def intersection(p1, p2, p3, p4):
    try:
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        if (x2 - x1 == 0):
            m2 = (y4 - y3) / (x4 - x3)
            return x1, int(m2 * x1 - m2* x3 + y3)
        elif (x4 - x3 == 0):
            m = (y2 - y1) / (x2 - x1)
            return x3, int(m * (x3 - x1) + y1)
        elif (y2 - y1 == 0):
            m2 = (y4 - y3) / (x4 - x3)
            return int((y1 - y3) / (m2 + x3)), y1
        elif (y4 - y3 == 0):
            m = (y2 - y1) / (x2 - x1)
            return int((y3 - y1) / m + x1), y3
        m = (y2 - y1) / (x2 - x1)
        m2 = (y4 - y3) / (x4 - x3)
        x = (m*x1 + y3 - m2 * x3 - y1) / (m - m2)
        y = ((1 / m - 1 / m2) ** -1) * (y1 / m - y3 / m2 + x3 - x1)
        return int(x), int(y)
    except:
        return None, None


def parse_lanes(lanes):
    lanes = [val for val in lanes if "[" in val]
    points = []
    mid = left = right = other = 0
    mid_pt = lanes.pop(0)
    mid = int(mid_pt.replace("[", ""))
    points.append(mid)
    for lane in lanes:
        lane = re.split('[(), ]', lane)
        lane = [2 * int(val) for val in lane if isInt(val)]
        points.append(lane)
        continue
        lane = lane[::2]
        pt = int(sum(lane) / len(lane))
        points.append(pt)
    return points


def interpolate(p1, p2, y3):
    top = p2[0] - p1[0]
    bot = p2[1] - p1[1]
    if bot == 0:
        return (p1[0], y3)
    diff = y3 - p1[1]
    return (int(top / bot * diff + p1[0]), y3)


def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1


def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr


class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]


class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]


class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]


#lib = CDLL("/home/pjreddie/documents/darknet/libdarknet.so", RTLD_GLOBAL)
#lib = CDLL("darknet.so", RTLD_GLOBAL)
hasGPU = True
if os.name == "nt":
    cwd = os.path.dirname(__file__)
    os.environ['PATH'] = cwd + ';' + os.environ['PATH']
    winGPUdll = os.path.join(cwd, "yolo_cpp_dll.dll")
    winNoGPUdll = os.path.join(cwd, "yolo_cpp_dll_nogpu.dll")
    envKeys = list()
    for k, v in os.environ.items():
        envKeys.append(k)
    try:
        try:
            tmp = os.environ["FORCE_CPU"].lower()
            if tmp in ["1", "true", "yes", "on"]:
                raise ValueError("ForceCPU")
            else:
                print("Flag value '"+tmp+"' not forcing CPU mode")
        except KeyError:
            # We never set the flag
            if 'CUDA_VISIBLE_DEVICES' in envKeys:
                if int(os.environ['CUDA_VISIBLE_DEVICES']) < 0:
                    raise ValueError("ForceCPU")
            try:
                global DARKNET_FORCE_CPU
                if DARKNET_FORCE_CPU:
                    raise ValueError("ForceCPU")
            except NameError:
                pass
            # print(os.environ.keys())
            # print("FORCE_CPU flag undefined, proceeding with GPU")
        if not os.path.exists(winGPUdll):
            raise ValueError("NoDLL")
        lib = CDLL(winGPUdll, RTLD_GLOBAL)
    except (KeyError, ValueError):
        hasGPU = False
        if os.path.exists(winNoGPUdll):
            lib = CDLL(winNoGPUdll, RTLD_GLOBAL)
            print("Notice: CPU-only mode")
        else:
            # Try the other way, in case no_gpu was
            # compile but not renamed
            lib = CDLL(winGPUdll, RTLD_GLOBAL)
            print("Environment variables indicated a CPU run, but we didn't find `" +
                  winNoGPUdll+"`. Trying a GPU run anyway.")
else:
    lib = CDLL("../zed-yolo/libdarknet/libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

if hasGPU:
    set_gpu = lib.cuda_set_device
    set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(
    c_int), c_int, POINTER(c_int), c_int]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

load_net_custom = lib.load_network_custom
load_net_custom.argtypes = [c_char_p, c_char_p, c_int, c_int]
load_net_custom.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)


def isInt(x):
    try: 
        int(x)
        return True
    except ValueError:
        return False




def array_to_image(arr):
    import numpy as np
    # need to return old values to avoid python freeing memory
    arr = arr.transpose(2, 0, 1)
    c = arr.shape[0]
    h = arr.shape[1]
    w = arr.shape[2]
    arr = np.ascontiguousarray(arr.flat, dtype=np.float32) / 255.0
    data = arr.ctypes.data_as(POINTER(c_float))
    im = IMAGE(w, h, c, data)
    return im, arr


def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        if altNames is None:
            nameTag = meta.names[i]
        else:
            nameTag = altNames[i]
        res.append((nameTag, out[i]))
    res = sorted(res, key=lambda x: -x[1])
    return res


def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45, debug=False):
    """
    Performs the detection
    """
    custom_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    custom_image = cv2.resize(custom_image, (lib.network_width(
        net), lib.network_height(net)), interpolation=cv2.INTER_LINEAR)
    im, arr = array_to_image(custom_image)
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(
        net, image.shape[1], image.shape[0], thresh, hier_thresh, None, 0, pnum, 0)
    num = pnum[0]
    if nms:
        do_nms_sort(dets, num, meta.classes, nms)
    res = []
    if debug:
        print("about to range")
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                if altNames is None:
                    nameTag = meta.names[i]
                else:
                    nameTag = altNames[i]
                res.append((nameTag, dets[j].prob[i], (b.x, b.y, b.w, b.h), i))
    res = sorted(res, key=lambda x: -x[1])
    free_detections(dets, num)
    return res


netMain = None
metaMain = None
altNames = None


def getObjectDepth(depth, bounds):
    area_div = 2

    x_vect = []
    y_vect = []
    z_vect = []

    for j in range(int(bounds[0] - area_div), int(bounds[0] + area_div)):
        for i in range(int(bounds[1] - area_div), int(bounds[1] + area_div)):
            z = depth[i, j, 2]
            if not np.isnan(z) and not np.isinf(z):
                x_vect.append(depth[i, j, 0])
                y_vect.append(depth[i, j, 1])
                z_vect.append(z)
    try:
        # Switched to np.median to avoid the statistics.median overflow 
        # error when using a uint8 depth map
        x = np.median(x_vect)
        y = np.median(y_vect)
        z = np.median(z_vect)
        #x = statistics.median(x_vect)
        #y = statistics.median(y_vect)
        #z = statistics.median(z_vect)
    except Exception:
        x = -1
        y = -1
        z = -1
        pass

    return x, y, z


def generateColor(metaPath):
    random.seed(42)
    f = open(metaPath, 'r')
    content = f.readlines()
    class_num = int(content[0].split("=")[1])
    color_array = []
    for x in range(0, class_num):
        color_array.append((randint(0, 255), randint(0, 255), randint(0, 255)))
    return color_array


def main(imgShape=None, memImgX=None, memImgY=None, memDepthX=None, memDepthY=None):
    saveVideo = True
    argv = []
    imgX8 = np.frombuffer(memImgX, dtype=np.int8).reshape(imgShape)
    imgY8 = np.frombuffer(memImgY, dtype=np.int8).reshape(imgShape)
    depthX8 = np.frombuffer(memDepthX, dtype=np.int8).reshape(imgShape)
    depthY8 = np.frombuffer(memDepthY, dtype=np.int8).reshape(imgShape)
    thresh = 0.25
    folderpath = "yolo/"
    darknet_path = folderpath
    configPath = folderpath + "yolov3-tiny.cfg"
    weightPath = folderpath + "yolov3-tiny.weights"
    metaPath = folderpath + "coco.data"
    svoPath = None

    imFromCamera = os.open("/tmp/camera_to_OD", os.O_RDONLY)
    lanes_pipe = os.open("/tmp/lanes_to_pp", os.O_RDONLY)
    #depthFromCamera = os.open("/tmp/depth_to_OD", os.O_RDONLY) # NOTE Not needed b/c can trigger with cam_to_od pipe
    objects_to_pp = os.open("/tmp/objects_to_pp", os.O_WRONLY)
    pp_to_lanes = os.open("/tmp/pp_to_lanes", os.O_WRONLY)
    pp_to_motor = os.open("/tmp/pp_to_motor", os.O_WRONLY)
    #TODO add pipe to path planning

    help_str = 'darknet_zed.py -c <config> -w <weight> -m <meta> -t <threshold> -s <svo_file>'
    try:
        opts, args = getopt.getopt(
            argv, "hc:w:m:t:s:", ["config=", "weight=", "meta=", "threshold=", "svo_file="])
    except getopt.GetoptError:
        print (help_str)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print (help_str)
            sys.exit()
        elif opt in ("-c", "--config"):
            configPath = arg
        elif opt in ("-w", "--weight"):
            weightPath = arg
        elif opt in ("-m", "--meta"):
            metaPath = arg
        elif opt in ("-t", "--threshold"):
            thresh = float(arg)
        elif opt in ("-s", "--svo_file"):
            svoPath = arg
    #can probably delete all this camera init stuff
    ''' 
    init = sl.InitParameters()
    init.coordinate_units = sl.UNIT.UNIT_METER
    if svoPath is not None:
        init.svo_input_filename = svoPath

    cam = sl.Camera()
    if not cam.is_opened():
        print("Opening ZED Camera...")
    status = cam.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit()
    
    runtime = sl.RuntimeParameters()
    # Use STANDARD sensing mode
    runtime.sensing_mode = sl.SENSING_MODE.SENSING_MODE_STANDARD
    '''
    mat = sl.Mat()
    point_cloud_mat = sl.Mat()

    # Import the global variables. This lets us instance Darknet once, then just call performDetect() again without instancing again
    global metaMain, netMain, altNames  # pylint: disable=W0603
    assert 0 < thresh < 1, "Threshold should be a float between zero and one (non-inclusive)"
    if not os.path.exists(configPath):
        raise ValueError("Invalid config path `" +
                         os.path.abspath(configPath)+"`")
    if not os.path.exists(weightPath):
        raise ValueError("Invalid weight path `" +
                         os.path.abspath(weightPath)+"`")
    if not os.path.exists(metaPath):
        raise ValueError("Invalid data file path `" +
                         os.path.abspath(metaPath)+"`")
    if netMain is None:
        netMain = load_net_custom(configPath.encode(
            "ascii"), weightPath.encode("ascii"), 0, 1)  # batch size = 1
    if metaMain is None:
        metaMain = load_meta(metaPath.encode("ascii"))
    if altNames is None:
        # In thon 3, the metafile default access craps out on Windows (but not Linux)
        # Read the names file and create a list to feed to detect
        try:
            with open(metaPath) as metaFH:
                metaContents = metaFH.read()
                import re
                match = re.search("names *= *(.*)$", metaContents,
                                  re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1)
                else:
                    result = None
                try:
                    if os.path.exists(result):
                        with open(result) as namesFH:
                            namesList = namesFH.read().strip().split("\n")
                            altNames = [x.strip() for x in namesList]
                except TypeError:
                    pass
        except Exception:
            pass

    color_array = generateColor(metaPath)
    print("Starting YOLO\n")
    frame_no = 0
    if saveVideo:
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("outputDN.avi", fourcc, 30.0, (320, 180))
    in_right = True
    curr_dodging = False
    tdodge = 0
    blocked = False
    commands = []
    kiyoshiBuffer = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    while True:  # for 'q' key
        # Do the detection
        if commands:
            c = commands.pop(0)
            if c == "g" or c == "h":
                os.write(pp_to_lanes, (c + "\0").encode())
            elif c == "d" or c == "b":
                os.write(pp_to_motor, (c + "\0").encode())

        imgIndexString = os.read(imFromCamera, 100).decode("utf8")
        #print("s: " + imgIndexString)
        imgIndex = int(imgIndexString[-2]) # read from end of pipe
        #print("Yolo:  " + imgIndexString + "  " + str(imgIndex))
        #print("Yolo:  " + str(frame_no))
        frame_no += 1
        if(imgIndex & 1 == 0):
            img = imgX8.astype(np.uint8)
            depth = depthX8.astype(np.uint8)
        elif(imgIndex & 1 == 1):
            img = imgY8.astype(np.uint8)
            depth = depthY8.astype(np.uint8)
        else:
            continue
        img = cv2.resize(img, (1280, 720))
        depth = cv2.resize(depth, (1280, 720))




        lane_pts = os.read(lanes_pipe, 2048).decode().split("|")
        if not blocked:
            if len(lane_pts) > 1:
                lane_pts = lane_pts[-2]
            try:
                lane_pts = lane_pts.split("]")
            except AttributeError:
                continue
            lanes = parse_lanes(lane_pts)
            left = lanes[1]
            right = lanes[2]
            topleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 0)
            bottomleft = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), 640)
            topright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 0)
            bottomright = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), 640)
            inter_x, inter_y = intersection(topleft, bottomleft, topright, bottomright)
            if inter_x is None:
                continue
            dleft = topleft[0] - bottomleft[0]
            #print(dleft)
            if inter_x < 0:
                inter_x = 0 + 20
            elif inter_x > 1279:
                inter_x = 1279 - 20
            if inter_y < 0:
                inter_y = 0 + 20
            elif inter_y > 719:
                inter_y = 719 - 20
            theleftline = interpolate((left[0]//2, left[1]//2), (left[2]//2, left[3]//2), inter_y + 20)
            therightline = interpolate((right[0]//2, right[1]//2), (right[2]//2, right[3]//2), inter_y + 20)
            theleftline = (theleftline[0] - 25, theleftline[1])
            therightline = (therightline[0] + 25, therightline[1])
        mid_rect = depth[inter_y+20:inter_y+40, theleftline[0]:therightline[0], 0]
        mid_rect = np.sort(mid_rect.flatten())
        length = mid_rect.size
        med = np.median(mid_rect[int(length * -0.15):])
        kiyoshiBuffer.pop(0)
        kiyoshiBuffer.append(med)


        width = int((therightline[0] - theleftline[0]) / 0.5)
        if in_right:
            adj_rect = depth[inter_y+20:inter_y+40, theleftline[0]-width-75:theleftline[0]-75, 0]
        else:
            adj_rect = depth[inter_y+20:inter_y+40, therightline[0]+75:therightline[0]+width+75, 0]
        adj_rect = np.sort(adj_rect.flatten())
        adj_med = np.median(adj_rect[int(length * -0.15):])

        cv2.rectangle(depth, (theleftline[0], inter_y + 20), (therightline[0], inter_y + 40), (0, 0, 255), 2)
        if in_right:
            cv2.rectangle(depth, (theleftline[0]-width-50, inter_y + 20), (theleftline[0]-50, inter_y + 40), (0, 0, 255), 2)
        else:
            cv2.rectangle(depth, (therightline[0]+50, inter_y + 20), (therightline[0]+width+50, inter_y + 40), (0, 0, 255), 2)

        #print(mid_rect[::60])
        #print(np.sort(mid_rect[:20, :20].flatten()))
        #med = np.median(mid_rect)
        cv2.circle(depth, (inter_x, inter_y+20), 5, (0, 0, 255), 4)
        #med = np.median(depth[inter_y-15:inter_y+15, inter_x-15:inter_x+15, 0])
        #med = 0
        #print(med):
        #print(str(adj_med) + "   " + str(med))
        #print(in_right)
        if blocked and np.median(kiyoshiBuffer) < 60:
            print("Driving forward!")
            if in_right:
                commands.append("H")
                commands.append("H")
                commands.append("H")
                commands.append("H")
                commands.append("H")
                commands.append("H")
                commands.append("G")
            else:
                commands.append("G")
                commands.append("G")
                commands.append("G")
                commands.append("G")
                commands.append("G")
                commands.append("G")
                commands.append("H")
            commands.append("d")
            blocked = False
        elif blocked and adj_med < 55:
            pass
            '''
            print("Driving around!")
            if in_right:
                print("Go left!")
                os.write(pp_to_lanes, ("g" + "\0").encode())
            else:
                print("Go right!")
                os.write(pp_to_lanes, ("h" + "\0").encode())
            os.write(pp_to_motor, ("d\0").encode())
            blocked = False
            in_right = not in_right
            curr_dodging = True
            tdodge = time.time()
            '''
        elif adj_med > 55 and med > 60 and (300 < dleft and dleft < 500):
            print("Blocked!   " + str(adj_med) + "   " + str(med))
            if not blocked:
                os.write(pp_to_motor, ("b\0").encode())
            kiyoshiBuffer = [med] * 10
            blocked = True
        elif not curr_dodging and med > 60 and (300 < dleft and dleft < 500): # change lanes
            print("dnet: Change lanes!   " + str(med))
            if in_right:
                print("Go left!")
                os.write(pp_to_lanes, ("g" + "\0").encode())
            else:
                print("Go right!")
                os.write(pp_to_lanes, ("h" + "\0").encode())
            in_right = not in_right
            curr_dodging = True
            tdodge = time.time()
        elif curr_dodging and time.time() - tdodge > 1.5:
            curr_dodging = False
        cv2.line(depth, topleft, bottomleft, (0, 255, 0), 3)
        cv2.line(depth, topright, bottomright, (0, 255, 0), 3)
        cv2.line(depth, (left[0]//2, left[1]//2), (left[2]//2, left[3]//2), (0, 0, 255), 3)
        cv2.line(depth, (right[0]//2, right[1]//2), (right[2]//2, right[3]//2), (0, 0, 255), 3)
        #cv2.circle(depth, (inter_x, inter_y), 5, (0, 0, 255), 4)
        #cv2.rectangle(depth, (inter_x - 15, inter_y - 15), (inter_x + 15, inter_y + 15), (0, 0, 255), 2)



        image = img
        detections = detect(netMain, metaMain, image, thresh)
        #print(chr(27) + "[2J"+"**** " +
        #str(len(detections)) + " Results ****")
        objects = []
        for detection in detections:
           label = detection[0]
           confidence = detection[1]
           pstring = label+": "+str(np.rint(100 * confidence))+"%"
           #print(pstring)
           bounds = detection[2]
           yExtent = int(bounds[3])
           xEntent = int(bounds[2])
           # Coordinates are around the center
           xCoord = int(bounds[0] - bounds[2]/2)
           yCoord = int(bounds[1] - bounds[3]/2)
           thickness = 1
           x, y, z = getObjectDepth(depth, bounds)
           distance = int(math.sqrt(x * x + y * y + z * z))
           #distance = "{:.2f}".format(distance)
           cv2.rectangle(image, (xCoord-thickness, yCoord-thickness), (xCoord + xEntent+thickness, yCoord+(18 +thickness*4)), color_array[detection[3]], -1)
           cv2.putText(image, label + " " +  (str(distance) + " m"), (xCoord+(thickness*4), yCoord+(10 +thickness*4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2)
           cv2.rectangle(image, (xCoord-thickness, yCoord-thickness), (xCoord + xEntent+thickness, yCoord + yExtent+thickness), color_array[detection[3]], int(thickness*2))
           boundingBox = ([xCoord, yCoord], [xCoord + xEntent, yCoord + yExtent], distance, label)
           objects.append(boundingBox)
        '''
        mid = 646
        dif = 75
        cv2.line(image, (mid - dif, 0), (mid - dif, 720), (0, 255, 0), 3)
        cv2.line(image, (mid + dif, 0), (mid + dif, 720), (0, 255, 0), 3)
        cv2.circle(image, (250, 640), 5, (0, 255, 255), 2)
        '''
        #cv2.imshow("darknet_zed: image", image)
        #cv2.imshow("darknet_zed: depth", depth)
        #cv2.waitKey(1)
        os.write(objects_to_pp, (str(objects) + "\0").encode())
        #print("Writing")
        if saveVideo:
            depth = cv2.resize(depth, (320, 180))
            out.write(depth)
    cv2.destroyAllWindows()

    cam.close()
    print("\nFINISH")


if __name__ == "__main__":
    main(sys.argv[1:])


