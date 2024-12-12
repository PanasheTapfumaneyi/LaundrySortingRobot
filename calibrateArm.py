#!/usr/bin/env python3
#coding=utf-8
import time
from Arm_Lib import Arm_Device

# Get DOFBOT object
Arm = Arm_Device()
time.sleep(.1)


# Function to clamp
def arm_clamp_block(enable):
    if enable == 0:
        Arm.Arm_serial_servo_write(6, 60, 400)  # 0 for Release(open)
    else:
        Arm.Arm_serial_servo_write(6, 135, 400)  # 1 for Clamp(close)
    time.sleep(0.5)

def arm_move(p, s_time = 500):
    for i in range(5):
        id = i + 1
        if id == 5:
            time.sleep(.1)
            Arm.Arm_serial_servo_write(id, p[i], int(s_time*1.2))
        else :
            Arm.Arm_serial_servo_write(id, p[i], s_time)
        time.sleep(.01)
    time.sleep(s_time/1000)

p_arm_position = [90, 130, 0, 0, 90]


# Make the DOFBOT move to a position ready to grab
arm_clamp_block(0)
arm_move(p_arm_position, 2000)
time.sleep(1)