# DOFBOT Control and Camera Feed

This project is a GUI application to sort laundry items based on their color/material using a Dofbot Robitic Arm, integrated with a live camera feed for detecting and sorting objects using Roboflow's machine learning inference API. The application includes functionality for object detection, robotic arm movement, and sorting items into bins.

## Requirements

### Hardware:
- DOFBOT Robotic Arm
- Webcam or external camera connected to your system

### Software:
- Python 3.7+
- Required Python libraries (listed below)

## Installation

1. **Clone or Download the Repository**
   ```bash
   git clone https://github.com/PanasheTapfumaneyi/LaundrySortingRobot
   cd LaundrySortingRobot
   ```

2. **Install Required Libraries**
   Run the following command to install the required Python libraries:
   ```bash
   pip install opencv-python Pillow tkinter Arm_Lib inference-sdk
   ```

3. **Setup Roboflow API**
   Ensure you have a Roboflow API key. The script includes a personal API key (`J2QdQ1rY8IvewifiImgk`).

## Usage

1. **Connect Hardware**
   - Connect the DOFBOT to your system.
   - Ensure the camera is connected and running.

2. **Run the Script**
   - Ensure the script is executed either in VNC viewer or directly on the DOFBOT machine via HDMI.
   - Before running the script, kill any existing arm control processes using the commands found in the official DOFBOT documentation.
   - Run the script using Python:
     ```bash
     python LaundrySortingClothes.py
     ```

3. **User Interface Features**
   - **Video Feed:** Displays the live camera feed.
   - **Status Display:** Shows the current status of the application
   - **Detecting hand gesture** Place hand in camera frame to initialize the program
   - **Buttons:**
     - **Start:** Begin the object detection and sorting.
     - **Stop:** Stop the sorting process.
     - **Set Timer:** Automatically stop the sorting process after a set time in seconds.
   - **Sorted Items Count:** Displays a count of sorted items.

4. **Predefined Arm Positions**
   - `p_detect`: Detection position.
   - `p_red_bin`: Red bin position.
   - `p_white_bin`: White bin position.
   - `p_wool_bin`: Wool bin position.

5. **Calibrating arm Positions**
   - Run calibrateArm.py to easily move arm around and test the servo angles

5. **Code for more accuracy**
   - For more acccuracy of the clothes detection, use the LaundrySortingBlocks.py as it uses a more accurate model based on colors alone

## Potential Errors

1. **Camera Not Detected**
   - Ensure the camera is properly connected.
   - Verify the camera permissions for your system.
   - Restart DOFBOT if errors persist



