from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event
import platform
import sys
import os
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton
from PyQt5.QtCore import QTimer
import pyqtgraph as pg  # Importing pyqtgraph for plotting

class SharedData:
    def __init__(self):
        self.values = None

class State:
    def __init__(self, device, shared_data):
        self.device = device
        self.samples = 0
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.shared_data = shared_data

    def data_handler(self, ctx, data):
        values = parse_value(data)
        self.shared_data.values = {'heading': values.heading, 'pitch': values.pitch, 'roll': values.roll, 'yaw': values.yaw}
        self.samples += 1
        # print(values)

# Redirigir stderr a /dev/null o a os.devnull
# sys.stderr = open(os.devnull, 'w')

# Where MAC1 = MAC address of MetaSensor
MAC1 = 'F1:1E:E2:6F:1D:E1'
device = MetaWear(MAC1)
device.connect()

shared_data = SharedData()
stateInstance = State(device, shared_data)

class SensorsInterface(QMainWindow):  # Define a class that inherits from QMainWindow
    def __init__(self, shared_data):
        super().__init__()  # Call the constructor of the parent class (QMainWindow)
        self.shared_data = shared_data

        self.setWindowTitle('Sensors Data in Real-Time')  # Set the window title
        self.setGeometry(100, 100, 1200, 600)  # Set the position and size of the window (x, y, width, height)

        # Main widget and layout
        self.main_widget = QWidget(self)  # Create a main widget
        self.setCentralWidget(self.main_widget)  # Set the main widget as the central widget of the window
        self.main_layout = QHBoxLayout(self.main_widget)  # Create a horizontal layout for the main widget

        # Plot widget
        self.plot_widget = pg.PlotWidget()  # Create a pyqtgraph plot widget
        self.main_layout.addWidget(self.plot_widget)  # Add the plot widget to the main layout

        # Data display and control layout
        self.control_widget = QWidget(self)  # Create a control widget
        self.control_layout = QVBoxLayout(self.control_widget)  # Create a vertical layout for the control widget
        self.main_layout.addWidget(self.control_widget)  # Add the control widget to the main layout

        # Labels for displaying data
        self.heading_label = QLabel("heading: 0.0")  # Label to display Accel Z-axis data
        self.pitch_label = QLabel("pitch: 0.0")  # Label to display Accel X-axis data
        self.roll_label = QLabel("roll: 0.0")  # Label to display Accel Y-axis data
        self.yaw_label = QLabel("yaw: 0.0")  # Label to display Accel Z-axis data

        # Add labels to the control layout
        self.control_layout.addWidget(self.heading_label)
        self.control_layout.addWidget(self.pitch_label)
        self.control_layout.addWidget(self.roll_label)
        self.control_layout.addWidget(self.yaw_label)

        # Start and Stop buttons
        self.start_button = QPushButton("Start")  # Button to start the data update
        self.stop_button = QPushButton("Stop")  # Button to stop the data update

        # Add buttons to the control layout
        self.control_layout.addWidget(self.start_button)
        self.control_layout.addWidget(self.stop_button)

        # Plot accel data arrays
        self.heading_data = np.array([])  # Initialize an empty array for Accel X-axis data
        self.pitch_data = np.array([])  # Initialize an empty array for Accel X-axis data
        self.roll_data = np.array([])  # Initialize an empty array for Accel Y-axis data
        self.yaw_data = np.array([])  # Initialize an empty array for Accel Z-axis data

        # Plot curves
        self.heading_curve = self.plot_widget.plot(pen=(255, 255, 255), name="heading-axis")  # Create a curve for Accel X-axis data with red color
        self.pitch_curve = self.plot_widget.plot(pen=(255, 0, 0), name="pitch-axis")  # Create a curve for Accel X-axis data with red color
        self.roll_curve = self.plot_widget.plot(pen=(0, 255, 0), name="roll-axis")  # Create a curve for Accel Y-axis data with green color
        self.yaw_curve = self.plot_widget.plot(pen=(0, 0, 255), name="yaw-axis")  # Create a curve for Accel Z-axis data with blue color

        # Timer for updating data
        self.timer = QTimer()  # Create a QTimer object
        self.timer.timeout.connect(self.update_data)  # Connect the timer's timeout signal to the update_data method

        # Connect buttons to methods
        self.start_button.clicked.connect(self.start_data)  # Connect the start button to the start_data method
        self.stop_button.clicked.connect(self.stop_data)  # Connect the stop button to the stop_data method

    def start_data(self):
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)

        libmetawear.mbl_mw_sensor_fusion_set_mode(device.board, SensorFusionMode.NDOF)
        libmetawear.mbl_mw_sensor_fusion_set_acc_range(device.board, SensorFusionAccRange._8G)
        libmetawear.mbl_mw_sensor_fusion_set_gyro_range(device.board, SensorFusionGyroRange._2000DPS)
        libmetawear.mbl_mw_sensor_fusion_write_config(device.board)

        # Subscribe to euler angles signal
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(device.board, SensorFusionData.EULER_ANGLE)
        libmetawear.mbl_mw_datasignal_subscribe(signal, None, stateInstance.callback)
        
        # Start sensor fusion (acc + gyro + mag + on-board sensor fusion algo)
        libmetawear.mbl_mw_sensor_fusion_enable_data(device.board, SensorFusionData.EULER_ANGLE)
        libmetawear.mbl_mw_sensor_fusion_start(device.board)

        # Create LED Pattern
        pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
        libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.BLINK)
        libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.GREEN)

        self.timer.start(100) # Start the timer to update data every 100 milliseconds

    def stop_data(self):
        # Stop and unsubscribe from accelerometer
        libmetawear.mbl_mw_sensor_fusion_stop(device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(device.board, SensorFusionData.EULER_ANGLE)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)

        # Remove the LED Pattern and Stop Playing
        libmetawear.mbl_mw_led_stop_and_clear(device.board)

        # Instructs the board to terminate the connection
        libmetawear.mbl_mw_debug_disconnect(device.board)

        self.timer.stop() # Stop the timer, stopping the data updates

    def update_data(self):
        if self.shared_data.values is not None:
            new_data = self.shared_data.values
            self.heading_data = np.append(self.heading_data, new_data['heading'])
            self.pitch_data = np.append(self.pitch_data, new_data['pitch'])
            self.roll_data = np.append(self.roll_data, new_data['roll'])
            self.yaw_data = np.append(self.yaw_data, new_data['yaw'])

            # Update the plot curves to show only the last 50 data points
            self.heading_curve.setData(self.heading_data[-50:])
            self.pitch_curve.setData(self.pitch_data[-50:])
            self.roll_curve.setData(self.roll_data[-50:])
            self.yaw_curve.setData(self.yaw_data[-50:])

            # Update the labels with the latest data
            self.heading_label.setText(f"Heading: {new_data['heading']:.2f}")
            self.pitch_label.setText(f"Pitch: {new_data['pitch']:.2f}")
            self.roll_label.setText(f"Roll: {new_data['roll']:.2f}")
            self.yaw_label.setText(f"Yaw: {new_data['yaw']:.2f}")

if __name__ == '__main__':
    app = QApplication(sys.argv)  # Create a QApplication
    window = SensorsInterface(shared_data)  # Create an instance of SensorsInterface
    window.show()  # Show the window
    sys.exit(app.exec())  # Start the application's event loop
