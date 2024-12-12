#!/usr/bin/env python3

# coding=utf-8

import cv2

import numpy as np

import time

from Arm_Lib import Arm_Device

import threading

from tkinter import Tk, Label

from PIL import Image, ImageTk

from inference_sdk import InferenceHTTPClient



# Initialize Roboflow client

CLIENT = InferenceHTTPClient(

    api_url="https://detect.roboflow.com",

    api_key="J2QdQ1rY8IvewifiImgk"

)



# Get DOFBOT object

Arm = Arm_Device()

time.sleep(0.1)



# Define clamp and move functions

def arm_clamp_block(enable):

    if enable == 0:

        Arm.Arm_serial_servo_write(6, 60, 400)  # Release

    else:

        Arm.Arm_serial_servo_write(6, 135, 400)  # Clamp

    time.sleep(0.5)



def arm_move(p, s_time=500):

    for i in range(5):

        id = i + 1

        if id == 5:

            time.sleep(0.1)

            Arm.Arm_serial_servo_write(id, p[i], int(s_time * 1.2))

        else:

            Arm.Arm_serial_servo_write(id, p[i], s_time)

        time.sleep(0.01)

    time.sleep(s_time / 1000)



# Define base positions

p_detect = [90, 130, 0, 0, 90]  # Detection position

p_red_bin = [175, 85, 35, 0, 90]  # Red bin position

p_white_bin = [10, 85, 30, 0, 90]  # White bin position

p_wool_bin = [40, 85, 30, 0, 90]  # Wool bin position



class RobotArmUI:

    def __init__(self, root):

        self.root = root

        self.root.title("DOFBOT Control and Camera Feed")

        

        self.video_frame = Label(root)

        self.video_frame.pack()



        self.status_label = Label(root, text="Status: Initializing...", fg="blue")

        self.status_label.pack()



        self.position_label = Label(root, text="Object Position: N/A", fg="black")

        self.position_label.pack()

        

        self.sorted_items_label = Label(root, text="Sorted Items: N/A", fg="black")

        self.sorted_items_label.pack()

        

        self.color_counts = {"red":0, "yellow":0, "green":0, "blue": 0}



        self.camera_running = True

        self.cap = cv2.VideoCapture(0)  # Open default camera

        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.1)

        self.cap.set(cv2.CAP_PROP_EXPOSURE, -4)



        self.video_thread = threading.Thread(target=self.update_camera_feed)

        self.video_thread.daemon = True

        self.video_thread.start()



        self.detection_thread = threading.Thread(target=self.run_detection_loop)

        self.detection_thread.daemon = True

        self.detection_thread.start()



    def update_camera_feed(self):

        while self.camera_running:

            ret, frame = self.cap.read()

            if not ret:

                continue



            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(cv2image)

            imgtk = ImageTk.PhotoImage(image=img)



            self.video_frame.imgtk = imgtk

            self.video_frame.configure(image=imgtk)



            time.sleep(0.03)  # Control frame rate



    def calculate_pickup_position(self, detection, frame_width, frame_height):

        """

        Calculate the arm positions based on object detection coordinates

        

        Args:

            detection (dict): Detection result from Roboflow

            frame_width (int): Width of the camera frame

            frame_height (int): Height of the camera frame

        

        Returns:

            list: Arm servo positions for picking up the object

        """

        # Extract object center coordinates

        x_center = detection['x']

        y_center = detection['y']



        # Normalize coordinates to servo angle adjustments

        # These values may need calibration based on your specific setup

        x_offset = int((x_center / frame_width - 0.5) * -35)  # Horizontal adjustment

        y_offset = int((y_center / frame_height - 0.5) * -35)  # Vertical adjustment



        # Base pickup position with dynamic adjustments

        pickup_position = [

            90 + x_offset,   # Base rotation (Servo 1)

            45 + y_offset,   # Shoulder angle (Servo 2)

            70,              # Elbow angle (Servo 3)

            0,               # Wrist angle (Servo 4)

            90               # Gripper orientation (Servo 5)

        ]



        # Ensure angles are within safe range

        pickup_position = [

            max(0, min(180, angle)) for angle in pickup_position

        ]



        return pickup_position



    def run_detection_loop(self):

        while self.camera_running:

            # Move to detection position

            self.status_label.config(text="Status: Moving to detection position...", fg="orange")

            self.root.update()

            arm_move(p_detect, 1000)

            time.sleep(1)



            # Capture an image from the camera

            ret, frame = self.cap.read()

            if not ret:

                self.status_label.config(text="Status: Camera error!", fg="red")

                return



            # Get frame dimensions

            frame_height, frame_width = frame.shape[:2]



            # Save the captured frame as an image

            cv2.imwrite("current_frame.jpg", frame)



            # Perform inference using Roboflow

            self.status_label.config(text="Status: Detecting with Roboflow...", fg="orange")

            self.root.update()

            result = CLIENT.infer("current_frame.jpg", model_id="square_pick/1")

            predictions = result.get("predictions", [])



            # Determine action based on the prediction

            if predictions:

                prediction = predictions[0]  # Use the top prediction

                label = prediction["class"]

                x_position = prediction['x']

                y_position = prediction['y']



                self.status_label.config(text=f"Status: Detected {label}", fg="green")

                self.position_label.config(text=f"Object Position: x={x_position}, y={y_position}", fg="black")

                self.root.update()

                

                # Calculate pickup position using frame dimensions

                pickup_pos = self.calculate_pickup_position(prediction, frame_width, frame_height)

                

                self.position_label.config(text=f"Pickup Position: {pickup_pos}", fg="black")

                self.root.update()

                

                self.handle_detection(label, pickup_pos)

            else:

                self.status_label.config(text="Status: No valid prediction found.", fg="red")

                self.position_label.config(text="Object Position: N/A", fg="black")

                self.root.update()



    def handle_detection(self, label, pickup_pos):

        if label == "red":

            bin_position = p_red_bin

            color = "red"

        elif label == "yellow":

            bin_position = p_white_bin

            color = "yellow"

        elif label == "green":

            bin_position = p_white_bin

            color = "green"

        elif label == "blue":

            bin_position = p_wool_bin

            color = "blue"

        else:

            self.status_label.config(text="Status: Unknown object detected.", fg="red")

            return

        

        self.color_counts[color] += 1

        

        self.update_sorted_items()



        self.move_and_clamp(pickup_pos, bin_position)

    

    def update_sorted_items(self):

        sorted_text = "\n".join([f"{color.capitalize()}: {count}" for color, count in self.color_counts.items()])

        self.sorted_items_label.config(text=f"Sorted Items:\n{sorted_text}")

        

    def move_and_clamp(self, pickup_pos, bin_position):

        self.status_label.config(text="Status: Moving to grab...", fg="orange")

        self.root.update()

        

        # Prepare grab position (slightly modified from original)

        grab_position = pickup_pos.copy()

        grab_position[2] = 58  # Adjust elbow

        grab_position[3] = 20   # Wrist angle

        grab_position[4] = 90  # Gripper orientation



        # Move to pickup position

        arm_move(grab_position, 3000)  # Slower movement for precision



        self.status_label.config(text="Status: Clamping object...", fg="orange")

        self.root.update()

        arm_clamp_block(1)

        

        # Lift object

        lift_position = grab_position.copy()

        lift_position[2] = 150  # Raise elbow slightly

        arm_move(lift_position, 2000)

        time.sleep(1)



        # Move to bin

        arm_move(bin_position, 2000)



        self.status_label.config(text="Status: Releasing object at bin...", fg="orange")

        self.root.update()

        arm_clamp_block(0)



        self.status_label.config(text="Status: Task complete! Resetting to detection...", fg="green")

        self.root.update()

        time.sleep(1)



    def close(self):

        self.camera_running = False

        self.cap.release()

        self.root.destroy()



# Main logic

try:

    root = Tk()

    app = RobotArmUI(root)

    root.protocol("WM_DELETE_WINDOW", app.close)

    root.mainloop()

except KeyboardInterrupt:

    print("Program interrupted.")

