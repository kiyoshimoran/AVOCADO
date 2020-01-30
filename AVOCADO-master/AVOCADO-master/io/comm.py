import socket
import time
import os
import select

#define MOTOR_TO_COMM "/tmp/motor_to_comm"
#define COMM_TO_PLATOONING_PID "/tmp/comm_to_platooning_pid"

def bytes_to_int(l):
    multiplier = 1
    total = 0
    for b in l:
        total += multiplier * b
        multiplier *= 255
    return total

def main():
    lcWrite = os.open("/tmp/comm_to_lane_change", os.O_WRONLY)
    freqRead = os.open("/tmp/freq_to_comm", os.O_RDONLY) # TODO Error check
    dutyWrite = os.open("/tmp/getting_comm_to_pid", os.O_WRONLY) # TODO Error check
    lcRead = os.open("/tmp/lane_change_to_comm", os.O_RDONLY)
    dutyRead = os.open("/tmp/motor_to_comm", os.O_RDONLY) # TODO Error check
    freqWrite = os.open("/tmp/other_freq_to_pid", os.O_WRONLY) # TODO Error check
    #toPlatoonPid = os.open("/tmp/comm_to_platooning_pid", os.O_WRONLY) # TODO Error check

    iAm = os.popen("sudo ifconfig").read()
    print("Starting comm.py")
    if ("192.168.0.101" in iAm):
        print("Follower")
        HOST = "192.168.0.102"
        follower(HOST, dutyWrite, freqWrite, lcWrite)
    else:
        print("Leader")
        leader(dutyRead, freqRead, lcRead)

def follower(HOST, dutyWrite, freqWrite, lcWrite):
    PORT = 6789
    message = "Hello"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as serr:
        for i in range(20):
            print(serr)
        if serr.errno == 98: # Address already in use
            print("comm.py: No connection, address already in use")
            while True:
                print("comm.py: No connection, address already in use")
                time.sleep(30) # no idea what to do
        else:
            raise serr
    t = time.time()
    connected = False
    while time.time() - t < 5:
        try:
            sock.connect(  (HOST, PORT)  )
            print("Host: " + HOST)
            connected = True
            break
        except:
            time.sleep(1)
    # TODO Fix search...doesn't seem to work very well
    if not connected:
        print("No platoons available. Will search for platoons every 20 seconds")
    while not connected:
        try:
            sock.connect(  (HOST, PORT)  )
            print("Found a platoon")
            print("Host: " + HOST)
            connected = True
        except:
            time.sleep(20)
    
    while True:
        t0 = time.time()
        s = (str(t0)).encode()
        #sock.sendall(s)
        #sock.sendall(str(t0).encode())
        try:
            data = sock.recv(1024)
        except:
            # TODO Change from blanket except
            continue
        # TODO Change from continues to getting most recent packet
        if not data: #TODO come up with better way to handle empty sockets or disconnects
            while True:
                time.sleep(1000)

        #print("|" + data + "|")
        try:
            if (data[0] != "(" or data[-1] != ")"):
                continue
            if ("(" in data[1:-1] or ")" in data[1:-1]):
                continue
            vals = data[1:-1].split(',')
            os.write(dutyWrite, (vals[0] + "\0").encode()) # write duty
        except: # TODO Change from blanket except
            continue
        #vals[1] = "0"
        #os.write(freqWrite, int(vals[1]))
        os.write(freqWrite, (vals[1] + "\0").encode()) # write freq
        if vals[2] == "g" or vals[2] == "h":
            os.write(lcWrite, (vals[2] + "\0").encode()) # write freq
        #print("Received speed:" + vals[0] + " " + vals[1])
    
    sock.close()

def leader(dutyRead, freqRead, lcRead):
    dutyPoll = select.poll()
    dutyPoll.register(dutyRead, select.POLLIN)
    freqPoll = select.poll()
    freqPoll.register(freqRead, select.POLLIN)
    lcPoll = select.poll()
    lcPoll.register(lcRead, select.POLLIN)

    HOST = ""
    PORT = 6789
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(  (HOST, PORT)  )
    except socket.error as serr:
        for i in range(20):
            print(serr)
        if serr.errno == 98: # Address already in use
            print("comm.py: No connection, address already in use")
            while True:
                print("comm.py: No connection, address already in use")
                time.sleep(30) # no idea what to do
        else:
            raise serr
    server.listen(5)
    
    print("Bound to " + HOST+":"+str(PORT))
    client, addr = server.accept()
       
    print("Connection from: " + addr[0]+":"+str(addr[1]))
    duty = "0"
    freq = "0"
    laneChange = "n" # (l)eft, (r)ight, (n)one
    change = 1
    in_right = True
    while True:
        if dutyPoll.poll(1):
            line = os.read(dutyRead, 10)#.decode("utf8")
            duty = str(ord(line[0])) # TODO Determine if better way to read as byte than ord
            change = 1
        if freqPoll.poll(1):
            line = os.read(freqRead, 10)#.decode("utf8")
            byte_list = [ord(i) for i in line]
            freq = str(bytes_to_int(byte_list))
            change = 1
        if lcPoll.poll(1):
            line = os.read(lcRead, 10)#.decode("utf8")
            try:
                if line[0] == "l":
                    laneChange = "g"
                    in_right = not in_right
                elif line[0] == "r":
                    laneChange = "h"
                    in_right = not in_right
                else:
                    laneChange = "n"
            except IndexError:
                continue
            change = 1
        else:
            laneChange = "n"
        if change:
            if in_right:
                packet = "(" + duty + "," + freq + "," + "t" + ")"
            else:
                packet = "(" + duty + "," + freq + "," + "f" + ")"
            try:
                for i in range(40):
                    client.sendall(packet)
            except:
                # TODO Change so not a blanket catch
                continue
            change = 0


if __name__ == "__main__":
    main()

