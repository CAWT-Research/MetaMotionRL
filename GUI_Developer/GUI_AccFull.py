from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event
import platform
import sys
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
        self.callback = FnVoid_VoidP_DataP(self.gyro_data_handler)
        self.shared_data = shared_data

    def gyro_data_handler(self, ctx, data):
        values = parse_value(data)
        self.shared_data.values = {'x': values.x, 'y': values.y, 'z': values.z}
        self.samples += 1
        print(f"x: {values.x}, y: {values.y}, z: {values.z}")

# Where MAC1 = MAC address of MetaSensor
# MAC1 = 'ED:5A:87:F4:51:74'
MAC1 = 'E1:E9:FC:FD:0C:70'
# MAC1 = 'F1:1E:E2:6F:1D:E1'
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
        self.x_label = QLabel("X-axis: 0.0")  # Label to display X-axis data
        self.y_label = QLabel("Y-axis: 0.0")  # Label to display Y-axis data
        self.z_label = QLabel("Z-axis: 0.0")  # Label to display Z-axis data

        # Add labels to the control layout
        self.control_layout.addWidget(self.x_label)
        self.control_layout.addWidget(self.y_label)
        self.control_layout.addWidget(self.z_label)

        # Start and Stop buttons
        self.start_button = QPushButton("Start")  # Button to start the data update
        self.stop_button = QPushButton("Stop")  # Button to stop the data update

        # Add buttons to the control layout
        self.control_layout.addWidget(self.start_button)
        self.control_layout.addWidget(self.stop_button)

        # Plot data arrays
        self.x_data = np.array([])  # Initialize an empty array for X-axis data
        self.y_data = np.array([])  # Initialize an empty array for Y-axis data
        self.z_data = np.array([])  # Initialize an empty array for Z-axis data

        # Plot curves
        self.x_curve = self.plot_widget.plot(pen='r', name="X-axis")  # Create a curve for X-axis data with red color
        self.y_curve = self.plot_widget.plot(pen='g', name="Y-axis")  # Create a curve for Y-axis data with green color
        self.z_curve = self.plot_widget.plot(pen='b', name="Z-axis")  # Create a curve for Z-axis data with blue color

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

        signal_acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_subscribe(signal_acc, None, stateInstance.callback)

        libmetawear.mbl_mw_acc_enable_acceleration_sampling(device.board)
        libmetawear.mbl_mw_acc_start(device.board)
        #___________________________________________________________________________________________________________________________
        pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
        libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.BLINK)
        libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.GREEN)

        libmetawear.mbl_mw_led_play(device.board)
        #___________________________________________________________________________________________________________________________

        self.timer.start(100)  # Start the timer to update data every 100 milliseconds

    def stop_data(self):
        libmetawear.mbl_mw_acc_stop(device.board)
        libmetawear.mbl_mw_acc_disable_acceleration_sampling(device.board)
        signal = libmetawear.mbl_mw_acc_get_acceleration_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)

        libmetawear.mbl_mw_led_stop_and_clear(device.board)

        self.timer.stop()  # Stop the timer, stopping the data updates

    def update_data(self):
        if self.shared_data.values is not None:
            new_data = self.shared_data.values
            self.x_data = np.append(self.x_data, new_data['x'])
            self.y_data = np.append(self.y_data, new_data['y'])
            self.z_data = np.append(self.z_data, new_data['z'])

            # Update the plot curves to show only the last 50 data points
            self.x_curve.setData(self.x_data[-50:])
            self.y_curve.setData(self.y_data[-50:])
            self.z_curve.setData(self.z_data[-50:])

            # Update the labels with the latest data
            self.x_label.setText(f"X-axis: {new_data['x']:.2f}")
            self.y_label.setText(f"Y-axis: {new_data['y']:.2f}")
            self.z_label.setText(f"Z-axis: {new_data['z']:.2f}")

if __name__ == '__main__':
    app = QApplication(sys.argv)  # Create a QApplication
    window = SensorsInterface(shared_data)  # Create an instance of SensorsInterface
    window.show()  # Show the window
    sys.exit(app.exec())  # Start the application's event loop
