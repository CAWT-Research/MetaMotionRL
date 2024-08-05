from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
import sys
import os
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QGridLayout
from PyQt5.QtCore import QTimer
import pyqtgraph as pg  # Importing pyqtgraph for plotting

class SharedData:
    def __init__(self):
        self.values = {'accel': None, 'gyro': None, 'mag': None}

class State:
    def __init__(self, device, shared_data):
        self.device = device
        self.samples = 0
        self.accel_callback = FnVoid_VoidP_DataP(self.accel_data_handler)
        self.gyro_callback = FnVoid_VoidP_DataP(self.gyro_data_handler)
        self.mag_callback = FnVoid_VoidP_DataP(self.mag_data_handler)
        self.shared_data = shared_data

    def accel_data_handler(self, ctx, data):
        values = parse_value(data)
        self.shared_data.values['accel'] = {'x': values.x, 'y': values.y, 'z': values.z}
        print(f"accel_x: {values.x}, accel_y: {values.y}, accel_z: {values.z}")
        self.combine_sensor_data()

    def gyro_data_handler(self, ctx, data):
        values = parse_value(data)
        self.shared_data.values['gyro'] = {'x': values.x, 'y': values.y, 'z': values.z}
        print(f"gyro_x: {values.x}, gyro_y: {values.y}, gyro_z: {values.z}")
        self.combine_sensor_data()
    
    def mag_data_handler(self, ctx, data):
        values = parse_value(data)
        self.shared_data.values['mag'] = {'x': values.x, 'y': values.y, 'z': values.z}
        print(f"mag_x: {values.x}, mag_y: {values.y}, mag_z: {values.z}")
        self.combine_sensor_data()

    def combine_sensor_data(self):
        accel = self.shared_data.values['accel']
        gyro = self.shared_data.values['gyro']
        mag = self.shared_data.values['mag']
        if accel and gyro and mag:
            combined_values = {
                'accel_x': accel['x'], 'accel_y': accel['y'], 'accel_z': accel['z'],
                'gyro_x': gyro['x'], 'gyro_y': gyro['y'], 'gyro_z': gyro['z'],
                'mag_x': mag['x'], 'mag_y': mag['y'], 'mag_z': mag['z']
            }
            self.shared_data.values = combined_values
            self.samples += 1
            # print(f"Combined values: {combined_values}")

# Redirigir stderr a /dev/null o a os.devnull
# sys.stderr = open(os.devnull, 'w')

# Where MAC1 = MAC address of MetaSensor
# MAC1 = 'F1:1E:E2:6F:1D:E1'
MAC1 = 'E1:E9:FC:FD:0C:70'
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

        # Grid layout for sensor data
        self.sensor_layout = QGridLayout()  # Create a grid layout for sensor data
        self.control_layout.addLayout(self.sensor_layout)  # Add the sensor layout to the control layout

        # Labels for displaying accelerometer data
        self.accel_x_label = QLabel("Accel X: 0.0")
        self.accel_y_label = QLabel("Accel Y: 0.0")
        self.accel_z_label = QLabel("Accel Z: 0.0")

        # Labels for displaying gyroscope data
        self.gyro_x_label = QLabel("Gyro X: 0.0")
        self.gyro_y_label = QLabel("Gyro Y: 0.0")
        self.gyro_z_label = QLabel("Gyro Z: 0.0")

        # Labels for displaying magnetometer data
        self.mag_x_label = QLabel("Mag X: 0.0")
        self.mag_y_label = QLabel("Mag Y: 0.0")
        self.mag_z_label = QLabel("Mag Z: 0.0")

        # Add accelerometer labels to the sensor layout
        self.sensor_layout.addWidget(self.accel_x_label, 0, 0)
        self.sensor_layout.addWidget(self.accel_y_label, 0, 1)
        self.sensor_layout.addWidget(self.accel_z_label, 0, 2)

        # Add gyroscope labels to the sensor layout
        self.sensor_layout.addWidget(self.gyro_x_label, 1, 0)
        self.sensor_layout.addWidget(self.gyro_y_label, 1, 1)
        self.sensor_layout.addWidget(self.gyro_z_label, 1, 2)

        # Add magnetometer labels to the sensor layout
        self.sensor_layout.addWidget(self.mag_x_label, 2, 0)
        self.sensor_layout.addWidget(self.mag_y_label, 2, 1)
        self.sensor_layout.addWidget(self.mag_z_label, 2, 2)

        # Start and Stop buttons
        self.start_button = QPushButton("Start")  # Button to start the data update
        self.stop_button = QPushButton("Stop")  # Button to stop the data update

        # Add buttons to the control layout
        self.control_layout.addWidget(self.start_button)
        self.control_layout.addWidget(self.stop_button)

        # Plot accel data arrays
        self.accel_x_data = np.array([])  # Initialize an empty array for Accel X-axis data
        self.accel_y_data = np.array([])  # Initialize an empty array for Accel Y-axis data
        self.accel_z_data = np.array([])  # Initialize an empty array for Accel Z-axis data

        # Plot gyro data arrays
        self.gyro_x_data = np.array([])  # Initialize an empty array for Gyro X-axis data
        self.gyro_y_data = np.array([])  # Initialize an empty array for Gyro Y-axis data
        self.gyro_z_data = np.array([])  # Initialize an empty array for Gyro Z-axis data

        # Plot mag data arrays
        self.mag_x_data = np.array([])  # Initialize an empty array for Mag X-axis data
        self.mag_y_data = np.array([])  # Initialize an empty array for Mag Y-axis data
        self.mag_z_data = np.array([])  # Initialize an empty array for Mag Z-axis data

        # Plot curves
        self.accel_x_curve = self.plot_widget.plot(pen=(255, 0, 0), name="Accel-X-axis")  # Create a curve for Accel X-axis data with red color
        self.accel_y_curve = self.plot_widget.plot(pen=(0, 255, 0), name="Accel-Y-axis")  # Create a curve for Accel Y-axis data with green color
        self.accel_z_curve = self.plot_widget.plot(pen=(0, 0, 255), name="Accel-Z-axis")  # Create a curve for Accel Z-axis data with blue color

        self.gyro_x_curve = self.plot_widget.plot(pen=(128, 0, 128), name="Gyro-X-axis")  # Create a curve for Gyro X-axis data with purple color
        self.gyro_y_curve = self.plot_widget.plot(pen=(192, 192, 192), name="Gyro-Y-axis")  # Create a curve for Gyro Y-axis data with silver color
        self.gyro_z_curve = self.plot_widget.plot(pen=(255, 165, 0), name="Gyro-Z-axis")  # Create a curve for Gyro Z-axis data with orange color

        self.mag_x_curve = self.plot_widget.plot(pen=(255, 20, 147), name="Mag-X-axis")  # Create a curve for Mag X-axis data with deep pink color
        self.mag_y_curve = self.plot_widget.plot(pen=(0, 255, 255), name="Mag-Y-axis")  # Create a curve for Mag Y-axis data with cyan color
        self.mag_z_curve = self.plot_widget.plot(pen=(255, 255, 0), name="Mag-Z-axis")  # Create a curve for Mag Z-axis data with yellow color

        # Connect buttons to their actions
        self.start_button.clicked.connect(self.start_data)  # Connect the start button to the start_data method
        self.stop_button.clicked.connect(self.stop_data)  # Connect the stop button to the stop_data method

        # QTimer for periodic data updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

    def update_data(self):
        if self.shared_data.values and isinstance(self.shared_data.values, dict) and 'accel_x' in self.shared_data.values:
            new_data = self.shared_data.values
            self.accel_x_data = np.append(self.accel_x_data, new_data['accel_x'])
            self.accel_y_data = np.append(self.accel_y_data, new_data['accel_y'])
            self.accel_z_data = np.append(self.accel_z_data, new_data['accel_z'])

            self.gyro_x_data = np.append(self.gyro_x_data, new_data['gyro_x'])
            self.gyro_y_data = np.append(self.gyro_y_data, new_data['gyro_y'])
            self.gyro_z_data = np.append(self.gyro_z_data, new_data['gyro_z'])

            self.mag_x_data = np.append(self.mag_x_data, new_data['mag_x'])
            self.mag_y_data = np.append(self.mag_y_data, new_data['mag_y'])
            self.mag_z_data = np.append(self.mag_z_data, new_data['mag_z'])

            # Update the plot curves to show only the last 50 data points
            self.accel_x_curve.setData(self.accel_x_data[-50:])
            self.accel_y_curve.setData(self.accel_y_data[-50:])
            self.accel_z_curve.setData(self.accel_z_data[-50:])

            self.gyro_x_curve.setData(self.gyro_x_data[-50:])
            self.gyro_y_curve.setData(self.gyro_y_data[-50:])
            self.gyro_z_curve.setData(self.gyro_z_data[-50:])

            self.mag_x_curve.setData(self.mag_x_data[-50:])
            self.mag_y_curve.setData(self.mag_y_data[-50:])
            self.mag_z_curve.setData(self.mag_z_data[-50:])

            # Update the labels with the latest data
            self.x_label.setText(f"Accel-X: {new_data['accel_x']:.2f}")
            self.y_label.setText(f"Accel-Y: {new_data['accel_y']:.2f}")
            self.z_label.setText(f"Accel-Z: {new_data['accel_z']:.2f}")

            self.gyro_x_label.setText(f"Gyro-X: {new_data['gyro_x']:.2f}")
            self.gyro_y_label.setText(f"Gyro-Y: {new_data['gyro_y']:.2f}")
            self.gyro_z_label.setText(f"Gyro-Z: {new_data['gyro_z']:.2f}")

            self.mag_x_label.setText(f"Mag-X: {new_data['mag_x']:.2f}")
            self.mag_y_label.setText(f"Mag-Y: {new_data['mag_y']:.2f}")
            self.mag_z_label.setText(f"Mag-Z: {new_data['mag_z']:.2f}")

    def start_data(self):
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)

        # Subscribe to accelerometer
        signal_acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_subscribe(signal_acc, None, stateInstance.accel_callback)
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(device.board)
        libmetawear.mbl_mw_acc_start(device.board)
        print("Acelerometro iniciado")

        # Subscribe to gyroscope
        signal_gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_subscribe(signal_gyro, None, stateInstance.gyro_callback)
        libmetawear.mbl_mw_gyro_bmi160_enable_rotation_sampling(device.board)
        libmetawear.mbl_mw_gyro_bmi160_start(device.board)
        print("Giroscopio iniciado")

        # Subscribe to magnetometer
        signal_mag = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_subscribe(signal_mag, None, stateInstance.mag_callback)
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(device.board)
        libmetawear.mbl_mw_mag_bmm150_start(device.board)
        print("Magnetometro iniciado")

        # Create LED Pattern
        pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
        libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.BLINK)
        libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.GREEN)

        self.timer.start(100)  # Start the timer to update data every 100 milliseconds
        libmetawear.mbl_mw_datasignal_subscribe(libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(device.board), None, stateInstance.mag_callback)

    def stop_data(self):
        # Stop and unsubscribe from accelerometer
        libmetawear.mbl_mw_acc_stop(device.board)
        libmetawear.mbl_mw_acc_disable_acceleration_sampling(device.board)
        signal_acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal_acc)

        # Stop and unsubscribe from gyroscope
        libmetawear.mbl_mw_gyro_bmi160_stop(device.board)
        libmetawear.mbl_mw_gyro_bmi160_disable_rotation_sampling(device.board)
        signal_gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal_gyro)

        libmetawear.mbl_mw_mag_bmm150_stop(device.board)
        libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(device.board)
        signal_mag = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(device.board)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal_mag)

        # Remove the LED Pattern and Stop Playing
        libmetawear.mbl_mw_led_stop_and_clear(device.board)

        self.timer.stop()  # Stop the timer, stopping the data updates

if __name__ == '__main__':
    app = QApplication(sys.argv)  # Create a QApplication
    window = SensorsInterface(shared_data)  # Create an instance of SensorsInterface
    window.show()  # Show the window
    sys.exit(app.exec())  # Start the application's event loop
