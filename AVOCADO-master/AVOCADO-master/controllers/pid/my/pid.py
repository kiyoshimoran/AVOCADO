
from matplotlib import pyplot as plt

class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.istate = 0
        self.dstate = 0
        self.pid = 0
        self.t = 0

    def get_response(self, t, error):
        # P Calc
        kp_response = self.kp * error
        # I Calc
        self.istate += error
        ki_response = self.ki * self.istate
        # D Calc
        try:
            kd_response = self.kd * (error - self.dstate)# / (t - self.t)
            self.t = t
        except ZeroDivisionError:
            self.dstate = error
            return self.pid
        except Exception as err:
            print("ERR: " + str(err))
            exit(-1)
        self.dstate = error
        # Sum responses
        total_response = kp_response + ki_response + kd_response
        self.pid = total_response
        return total_response


def main():
    fin = open("pidSHORT.csv", "r")
    pid = PID(8.7, 0.02, 2.5)
    times = []
    me = []
    them = []
    count = 0
    for line in fin:
        l = line.strip().split(',')
        t = float(l[0])
        c_input = float(l[1])
        c_output = float(l[2])
        times.append(t)
        them.append(c_output)
        my_response = pid.get_response(t, c_input)
        print(my_response)
        me.append(my_response + 0.00000000000001)
        #print(c_output - my_response)
        count += 1
        '''
        if (count == 20):
            break
        '''
    plt.plot(times, me, times, them)
    plt.show()
    fin.close()

if __name__ == "__main__":
    main()
