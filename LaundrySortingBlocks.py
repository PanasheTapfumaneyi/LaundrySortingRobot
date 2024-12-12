from tkinter import Tk, Label, Button, Entry
import threading
import time
import cv2
from PIL import Image, ImageTk
from Arm_Lib import Arm_Device
from inference_sdk import InferenceHTTPClient

# Initialize Roboflow client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="J2QdQ1rY8IvewifiImgk"
)

# Get DOFBOT object
Arm = Arm_Device()
time.sleep(0.1)



# Function to clamp
def arm_clamp_block(enable):
    if enable == 0:
        Arm.Arm_serial_servo_write(6, 60, 400)  # 0 for Release(open)
    else:
        Arm.Arm_serial_servo_write(6, 135, 400)  # 1 for Clamp(close)
    time.sleep(0.5)


#Function to move the arm, p: list of the servo angles, s_time: movement duration
def arm_move(p, s_time=500):
    for i in range(5):
        id = i + 1
        if id == 5:
            time.sleep(0.1)
            Arm.Arm_serial_servo_write(id, p[i], int(s_time * 1.2)) 
        else:
            Arm.Arm_serial_servo_write(id, p[i], s_time)
        time.sleep(0.01)
    time.sleep(s_time / 1000) #Waiting for movements to be completed before moving on 



# Predefined positions for the arm

p_detect = [90, 130, 0, 0, 90]  # Object detection position
p_red_bin = [175, 85, 35, 0, 90]  # Red bin position
p_white_bin = [10, 85, 30, 0, 90]  # White bin position
p_wool_bin = [40, 85, 30, 0, 90]  # Wool bin position


#User Interface
class RobotArmUI:

    def __init__(self, root):
        #Initializing main UI window
        self.root = root
        self.root.title("DOFBOT Control and Camera Feed")
        self.root.geometry("400x300")

        #Video frames
        self.video_frame = Label(root)
        self.video_frame.pack()

        #Status labels initial state 
        self.status_label = Label(root, text="Status: Initializing...", fg="blue")
        self.status_label.pack()
        self.position_label = Label(root, text="Object Position: N/A", fg="black")
        self.position_label.pack()
        self.sorted_items_label = Label(root, text="Sorted Items: N/A", fg="black")
        self.sorted_items_label.pack()
        self.timer_label = Label(root, text="Set Timer (seconds):")
        self.timer_label.pack()
        self.timer_entry = Entry(root)
        self.timer_entry.pack()

        # Defining buttons
        self.start_button = Button(root, text="Start", command=self.start_sorting)
        self.start_button.pack()
        self.stop_button = Button(root, text="Stop", command=self.stop_sorting, state="disabled")
        self.stop_button.pack()
        self.timer_button = Button(root, text="Set Timer", command=self.set_timer)
        self.timer_button.pack()

 
        
        #Initializing variables
        self.color_counts = {"colors": 0, "white": 0, "wool": 0}


        # Start the camera
        self.camera_running = True

        # Set the sorting state
        self.sorting_active = False

        # Set the sorting ti9mes start 
        self.sorting_timer = None

        # Open the default camera
        self.cap = cv2.VideoCapture(0)
        
        
        self.gesture_thread = threading.Thread(target=self.detect_gesture)
        self.gesture_thread.daemon = True
        self.gesture_thread.start()

        # Start camera feed and update the thread
        self.video_thread = threading.Thread(target=self.update_camera_feed)
        self.video_thread.daemon = True
        self.video_thread.start()


    # Function to control the camera feed
    def update_camera_feed(self):
        # While loop to constantly update the camera feed
        while self.camera_running:
            ret, frame = self.cap.read()
            if not ret:
                # Skip iteration if the frame has not caprured
                continue

            # Convert frame to RGB
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_frame.imgtk = imgtk
            self.video_frame.configure(image=imgtk)

            time.sleep(0.03)  # Definr frame rate

    # Function to start the sorting process
    def start_sorting(self):
        self.status_label.config(text="Status: Sorting started.", fg="green")
        self.sorting_active = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.detection_thread = threading.Thread(target=self.run_detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        b_time = 1
        Arm.Arm_Buzzer_On(b_time)
        time.sleep(1)

    # Function to stop the sorting process
    def stop_sorting(self):
        self.status_label.config(text="Status: Sorting stopped.", fg="red")
        self.sorting_active = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        b_time = 1
        Arm.Arm_Buzzer_On(b_time)
        time.sleep(1)
        b_time = 1
        Arm.Arm_Buzzer_On(b_time)
        time.sleep(1)

    # Function to set a timer to stop sorting
    def set_timer(self):
        try:
            duration = int(self.timer_entry.get())
            if self.sorting_timer:
                self.sorting_timer.cancel()
            self.sorting_timer = threading.Timer(duration, self.stop_sorting)
            self.sorting_timer.start()
            self.status_label.config(text=f"Status: Timer set for {duration} seconds.", fg="blue")
        except ValueError:
            self.status_label.config(text="Status: Invalid timer value!", fg="red")

    # Function to detect the clothes using a loop 
    def run_detection_loop(self):
        while self.sorting_active:
            arm_move(p_detect, 1000)
            time.sleep(1)
            ret, frame = self.cap.read()
            if not ret:
                self.status_label.config(text="Status: Camera error!", fg="red")
                return
            frame_height, frame_width = frame.shape[:2]
            # Save the current frame and use it to detect the object
            cv2.imwrite("current_frame.jpg", frame) 
            self.status_label.config(text="Status: Detecting with Roboflow...", fg="orange")
            result = CLIENT.infer("current_frame.jpg", model_id="square_pick/1")
            predictions = result.get("predictions", [])

            # Display prediction results store the position of the detected object
            if predictions:
                prediction = predictions[0]
                label = prediction["class"]
                x_position = prediction['x']
                y_position = prediction['y']
                self.status_label.config(text=f"Status: Detected {label}", fg="green")
                pickup_pos = self.calculate_pickup_position(prediction, frame_width, frame_height)
                self.handle_detection(label, pickup_pos)
            else:
                self.status_label.config(text="Status: No valid prediction found.", fg="red")
                
    #Function to detect hand gestures to initialize program
    def detect_gesture(self):
        while self.camera_running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame_path = "gesture_frame.jpg"
            cv2.imwrite(frame_path, frame)

            # Preprocess image
            preprocessed_path = frame_path

            # Perform inference using Roboflow for gestures
            result = CLIENT.infer(preprocessed_path, model_id="hand_detect-xhlhk/2")
            predictions = result.get("predictions", [])

            if predictions:
                gesture = predictions[0]["class"]

                if gesture == "hand":
                    self.status_label.config(text="Status: Program Started", fg="green")
                    self.detection_thread = threading.Thread(target=self.run_detection_loop)
                    self.detection_thread.daemon = True
                    self.detection_thread.start()

            time.sleep(1)

    # Function to calculate the position to pick up a block
    def calculate_pickup_position(self, detection, frame_width, frame_height):
        x_center = detection['x']
        y_center = detection['y']
        x_offset = int((x_center / frame_width - 0.5) * -35)
        y_offset = int((y_center / frame_height - 0.5) * -35)
        pickup_position = [90 + x_offset, 45 + y_offset, 70, 0, 90]
        return [max(0, min(180, angle)) for angle in pickup_position]

    # Function to define the bin position that the clothes need to go based on the prediction result
    def handle_detection(self, label, pickup_pos):
        if label == "red":
            bin_position = p_red_bin
            color = "colors"
        elif label == "yellow":
            bin_position = p_white_bin
            color = "white"
        elif label == "green":
            bin_position = p_white_bin
            color = "colors"
        elif label == "blue":
            bin_position = p_wool_bin
            color = "wool"
        else:
            self.status_label.config(text="Status: Unknown object detected.", fg="red")
            return

        # Add one to the detected color each time it is sorted
        self.color_counts[color] += 1
        self.update_sorted_items()
        # Move and clamp the arm based on the pickup position and bin position
        self.move_and_clamp(pickup_pos, bin_position)

    # Function to update the count for the sorted items
    def update_sorted_items(self):
        sorted_text = "\n".join([f"{color.capitalize()}: {count}" for color, count in self.color_counts.items()])
        self.sorted_items_label.config(text=f"Sorted Items:\n{sorted_text}")

    # Function to move and clamp the clothes based on the calculated position
    def move_and_clamp(self, pickup_pos, bin_position):
        grab_position = pickup_pos.copy()
        grab_position[2] = 58
        grab_position[3] = 20
        grab_position[4] = 90
        arm_move(grab_position, 3000)
        arm_clamp_block(1)
        lift_position = grab_position.copy()
        lift_position[2] = 150
        arm_move(lift_position, 2000)
        arm_move(bin_position, 2000)
        arm_clamp_block(0)


    # Function to close and clear the resources
    def close(self):
        self.camera_running = False
        self.cap.release()
        self.root.destroy()

# Running the application
try:
    root = Tk()
    app = RobotArmUI(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
except KeyboardInterrupt:
    print("Program interrupted.")

