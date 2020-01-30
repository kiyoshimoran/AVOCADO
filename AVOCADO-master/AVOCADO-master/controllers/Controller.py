# -*- coding: utf-8 -*-
## @file Controller.py
#  @package Controller
#  @authors Jacob Loh, Josh Neiman

import pyb

## This class implements a P-only controller
class Controller:

    ## Initializes a P-only controller.
    #  @param setpoint (int): initial setpoint for the controller to track
    #  @param kp (int): initial value of proportional gain in the controller
    def __init__(self, setpt, kp, ki): # kp=0, ki=0, kd=0):
        ## setpt: input signal for the controller to track
        self.setpoint = setpt
        ## kp: proportional gain to be used by the controller
        self.kp = kp
        self.ki = ki # available for further development of controller
        self.integral = 0
        '''
        self.kd = kd # available for further development of controller
        '''

    ## Updates setpoint
    #  @param setpt (int): new target setpoint for the controller
    #  @return (boolean): True indicating the set method succeeded
    def set_setpoint(self, setpt):
        self.setpoint = setpt
        return True

    ## Updates proportional gain
    #  @param setpt (int): new proportional gain for the controller
    #  @return (boolean): True indicating the set method succeeded
    def set_kp(self, kp):
        self.kp = kp
        return True

    ## Gets controller output
    #  @param pos (int): target position of the system
    #  @return (int): magnitude of the required controller response
    def get_response(self, pos):
        error = pos - self.setpoint
        self.integral += error
        kp_response = error * self.kp
        ki_response = self.integral * self.ki
        kd_response = 0
        total = kp_response + ki_response + kd_response
        if (total > 100):
            total = 100
        elif (total < -100):
            total = -100
        return total
