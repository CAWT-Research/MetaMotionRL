## This code give us the euler angles of de N sensors MbientLab MetaWear connected to the graphical interface
## In this moment the code give us an excel with the information for the training data, preliminary we have the
## Implementation with two sensors for training a neural network for the arm

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep, time
from threading import Thread, Lock
import platform
import sys
import os
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import pandas as pd
from datetime import datetime

class SharedData:
    def __init__(self):
        self.values = {}

class State:
    def __init__(self, device, shared_data, mac_address):
        self.device = device
        self.samples = 0
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.shared_data = shared_data
        self.mac_address = mac_address
        self.last_capture_time = time()  # Track the time of last capture

    def data_handler(self, ctx, data):
        values = parse_value(data)
        timestamp = datetime.now().strftime('%H:%M:%S.%f')
        if self.mac_address not in self.shared_data.values:
            self.shared_data.values[self.mac_address] = []
        
        # Ensure the time between captures is consistent
        current_time = time()
        if current_time - self.last_capture_time < 0.1:  # Adjust this value if needed
            sleep(0.1 - (current_time - self.last_capture_time))
        self.last_capture_time = time()

        self.shared_data.values[self.mac_address].append({
            'timestamp': timestamp,
            'heading': values.heading, 
            'pitch': values.pitch, 
            'roll': values.roll, 
            'yaw': values.yaw
        })
        self.samples += 1

def connect_sensor(mac_address):
    device = MetaWear(mac_address)
    device.connect()
    print(f"Conectado al sensor {mac_address}")
    return device

def capture_data(device, shared_data, lock, mac_address):
    state_instance = State(device, shared_data, mac_address)
    
    libmetawear.mbl_mw_settings_set_connection_parameters(device.board, 7.5, 100, 0, 6000)
    sleep(1.5)

    libmetawear.mbl_mw_sensor_fusion_set_mode(device.board, SensorFusionMode.NDOF)
    libmetawear.mbl_mw_sensor_fusion_set_acc_range(device.board, SensorFusionAccRange._8G)
    libmetawear.mbl_mw_sensor_fusion_set_gyro_range(device.board, SensorFusionGyroRange._2000DPS)
    libmetawear.mbl_mw_sensor_fusion_write_config(device.board)

    signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(device.board, SensorFusionData.EULER_ANGLE)
    libmetawear.mbl_mw_datasignal_subscribe(signal, None, state_instance.callback)
    
    libmetawear.mbl_mw_sensor_fusion_enable_data(device.board, SensorFusionData.EULER_ANGLE)
    libmetawear.mbl_mw_sensor_fusion_start(device.board)

    pattern = LedPattern(repeat_count=Const.LED_REPEAT_INDEFINITELY)
    libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.BLINK)
    libmetawear.mbl_mw_led_write_pattern(device.board, byref(pattern), LedColor.GREEN)

    while getattr(device, 'streaming', True):
        sleep(0.1)  # Sleep for a short duration to avoid busy-waiting

    libmetawear.mbl_mw_sensor_fusion_stop(device.board)
    libmetawear.mbl_mw_datasignal_unsubscribe(signal)
    libmetawear.mbl_mw_led_stop_and_clear(device.board)
    print(f"Detenido el sensor {mac_address}")

class SensorsInterface(QMainWindow):
    def __init__(self, shared_data):
        super().__init__()
        self.shared_data = shared_data
        self.setWindowTitle('Sensors Data in Real-Time')
        self.setGeometry(100, 100, 1200, 600)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        self.plot_widget = pg.PlotWidget()
        self.main_layout.addWidget(self.plot_widget)

        self.control_widget = QWidget(self)
        self.control_layout = QVBoxLayout(self.control_widget)
        self.main_layout.addWidget(self.control_widget)

        self.connect_button = QPushButton("Connect")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.control_layout.addWidget(self.connect_button)
        self.control_layout.addWidget(self.start_button)
        self.control_layout.addWidget(self.stop_button)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

        self.connect_button.clicked.connect(self.connect_sensors)
        self.start_button.clicked.connect(self.start_data)
        self.stop_button.clicked.connect(self.stop_data)

        # self.sensor_addresses = ['F1:1E:E2:6F:1D:E1', 'EE:1B:72:FA:BF:E8']
        self.sensor_addresses = ['F1:1E:E2:6F:1D:E1']
        self.devices = []
        self.threads = []
        self.lock = Lock()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.labels = {}
        self.data = {}
        self.curves = {}

    def connect_sensors(self):
        try:
            for mac in self.sensor_addresses:
                device = connect_sensor(mac)
                self.devices.append(device)

                self.labels[mac] = {
                    'heading': QLabel(f"{mac} heading: 0.0"),
                    'pitch': QLabel(f"{mac} pitch: 0.0"),
                    'roll': QLabel(f"{mac} roll: 0.0"),
                    'yaw': QLabel(f"{mac} yaw: 0.0")
                }
                for label in self.labels[mac].values():
                    self.control_layout.addWidget(label)

                self.data[mac] = {
                    'heading': np.array([]),
                    'pitch': np.array([]),
                    'roll': np.array([]),
                    'yaw': np.array([])
                }
                self.curves[mac] = {
                    'heading': self.plot_widget.plot(pen=(255, 255, 255), name=f"{mac} heading-axis"),
                    'pitch': self.plot_widget.plot(pen=(255, 0, 0), name=f"{mac} pitch-axis"),
                    'roll': self.plot_widget.plot(pen=(0, 255, 0), name=f"{mac} roll-axis"),
                    'yaw': self.plot_widget.plot(pen=(0, 0, 255), name=f"{mac} yaw-axis")
                }

            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al conectar los sensores: {str(e)}")
            self.devices = []
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def start_data(self):
        try:
            for device in self.devices:
                device.streaming = True
                thread = Thread(target=capture_data, args=(device, self.shared_data, self.lock, device.address))
                self.threads.append(thread)
                thread.start()

            self.timer.start(100)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al iniciar la captura de datos: {str(e)}")

    def stop_data(self):
        try:
            for device in self.devices:
                device.streaming = False

            for thread in self.threads:
                thread.join()

            for device in self.devices:
                libmetawear.mbl_mw_debug_disconnect(device.board)
                device.disconnect()
                print(f"Desconectado el sensor {device.address}")

            self.timer.stop()

            writer = pd.ExcelWriter('sensor_data.xlsx', engine='xlsxwriter')
            # Synchronize data before saving
            min_samples = min(len(self.shared_data.values[mac]) for mac in self.sensor_addresses)
            for mac, data_list in self.shared_data.values.items():
                if data_list:
                    self.shared_data.values[mac] = data_list[:min_samples]  # Trim excess data
                    # Replace invalid characters in the sheet name
                    safe_mac = mac.replace(':', '_')
                    df = pd.DataFrame(data_list)
                    df.to_excel(writer, sheet_name=safe_mac, index=False)
            writer.close()
            print("Datos guardados en sensor_data.xlsx")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al detener la captura de datos: {str(e)}")

    def update_data(self):
        for mac, new_data in self.shared_data.values.items():
            if new_data:
                latest_data = new_data[-1]
                self.data[mac]['heading'] = np.append(self.data[mac]['heading'], latest_data['heading'])
                self.data[mac]['pitch'] = np.append(self.data[mac]['pitch'], latest_data['pitch'])
                self.data[mac]['roll'] = np.append(self.data[mac]['roll'], latest_data['roll'])
                self.data[mac]['yaw'] = np.append(self.data[mac]['yaw'], latest_data['yaw'])

                self.curves[mac]['heading'].setData(self.data[mac]['heading'][-50:])
                self.curves[mac]['pitch'].setData(self.data[mac]['pitch'][-50:])
                self.curves[mac]['roll'].setData(self.data[mac]['roll'][-50:])
                self.curves[mac]['yaw'].setData(self.data[mac]['yaw'][-50:])

                self.labels[mac]['heading'].setText(f"{mac} Heading: {latest_data['heading']:.2f}")
                self.labels[mac]['pitch'].setText(f"{mac} Pitch: {latest_data['pitch']:.2f}")
                self.labels[mac]['roll'].setText(f"{mac} Roll: {latest_data['roll']:.2f}")
                self.labels[mac]['yaw'].setText(f"{mac} Yaw: {latest_data['yaw']:.2f}")

if __name__ == '__main__':
    shared_data = SharedData()
    app = QApplication(sys.argv)
    window = SensorsInterface(shared_data)
    window.show()
    sys.exit(app.exec())
