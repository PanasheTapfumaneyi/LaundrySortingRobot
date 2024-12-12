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

        self.color_counts = {"color": 0, "white": 0, "wool": 0}

        self.camera_running = True
        self.cap = cv2.VideoCapture(0)  # Open default camera
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.1)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, -4)

        self.running = False  # Control flag for the main program

        self.video_thread = threading.Thread(target=self.update_camera_feed)
        self.video_thread.daemon = True
        self.video_thread.start()

        self.detection_thread = threading.Thread(target=self.run_detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()

        self.gesture_thread = threading.Thread(target=self.detect_gesture)
        self.gesture_thread.daemon = True
        self.gesture_thread.start()

    def update_camera_feed(self):
        while self.camera_running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Crop to simulate zoom effect
            frame_height, frame_width = frame.shape[:2]
            crop_size = min(frame_width, frame_height) // 2  # Zoom factor (adjust as needed)
            center_x, center_y = frame_width // 2, frame_height // 2
            cropped_frame = frame[center_y - crop_size:center_y + crop_size, center_x - crop_size:center_x + crop_size]

            # Resize to 640x640
            zoomed_frame = cv2.resize(cropped_frame, (640, 640))

            # Convert to Tkinter-compatible image
            cv2image = cv2.cvtColor(zoomed_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_frame.imgtk = imgtk
            self.video_frame.configure(image=imgtk)

            time.sleep(0.03)  # Control frame rate

    def preprocess_image(self, image_path):
        """
        Preprocess the image for inference by resizing to 640x640.
        
        Args:
            image_path (str): Path to the image to be preprocessed.
        
        Returns:
            str: Path to the preprocessed image.
        """
        image = cv2.imread(image_path)
        resized_image = cv2.resize(image, (640, 640))
        preprocessed_path = "preprocessed_frame.jpg"
        cv2.imwrite(preprocessed_path, resized_image)
        return preprocessed_path

    def run_detection_loop(self):
        while self.camera_running:
            if not self.running:
                time.sleep(0.5)  # Skip iteration if not running
                continue

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

            # Save the captured frame as an image
            frame_path = "current_frame.jpg"
            cv2.imwrite(frame_path, frame)

            # Preprocess the image
            preprocessed_path = self.preprocess_image(frame_path)

            # Perform inference using Roboflow
            self.status_label.config(text="Status: Detecting with Roboflow...", fg="orange")
            self.root.update()
            result = CLIENT.infer(preprocessed_path, model_id="laundry-inckb/7")
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
                
                # Calculate pickup position
                frame_height, frame_width = frame.shape[:2]
                pickup_pos = self.calculate_pickup_position(prediction, frame_width, frame_height)
                
                self.position_label.config(text=f"Pickup Position: {pickup_pos}", fg="black")
                self.root.update()
                
                self.handle_detection(label, pickup_pos)
            else:
                self.status_label.config(text="Status: No valid prediction found.", fg="red")
                self.position_label.config(text="Object Position: N/A", fg="black")
                self.root.update()

    def detect_gesture(self):
        """
        Continuously detect gestures to start or stop the program.
        """
        while self.camera_running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Save the captured frame as an image
            frame_path = "gesture_frame.jpg"
            cv2.imwrite(frame_path, frame)

            # Preprocess the image
            preprocessed_path = self.preprocess_image(frame_path)

            # Perform inference using Roboflow for gestures
            result = CLIENT.infer(preprocessed_path, model_id="hand-gestures-abcde/1")
            predictions = result.get("predictions", [])

            if predictions:
                gesture = predictions[0]["class"]

                if gesture == "start" and not self.running:
                    self.running = True
                    self.status_label.config(text="Status: Program Started", fg="green")
                elif gesture == "stop" and self.running:
                    self.running = False
                    self.status_label.config(text="Status: Program Stopped", fg="red")

            time.sleep(1)  # Adjust for gesture detection frequency

    def calculate_pickup_position(self, detection, frame_width, frame_height):
        # (Implementation as in original code)
        pass

    def handle_detection(self, label, pickup_pos):
        # (Implementation as in original code)
        pass

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
