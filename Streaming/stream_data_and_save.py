# Stream data of sensors for amount of samples be nearest and save it in a workbook
# Stream of acceleration, gyroscope and magnetometer in the three axis x, y, and z
# Workbook structure:
# sample_count' 'sensor_index' 'epoch' 'gyro_x' 'gyro_y' 'gyro_z' 'accel_x' 'accel_y' 'accel_z' 'mag_x' 'mag_y' 'mag_z'
from __future__ import print_function
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Thread, Event, Lock
import csv
import platform
import sys
from queue import Queue

if sys.version_info[0] == 2:
    range = xrange

class State:
    def __init__(self, device, index):
        self.device = device
        self.samples = 0
        self.index = index
        self.gyro_data = None
        self.acc_data = None
        self.mag_data = None
        self.callbacks = {
            'gyro': FnVoid_VoidP_DataP(self.gyro_data_handler),
            'acc': FnVoid_VoidP_DataP(self.acc_data_handler),
            'mag': FnVoid_VoidP_DataP(self.mag_data_handler)
        }
                
    def gyro_data_handler(self, ctx, data):
        values = parse_value(data)
        self.gyro_data = [data.contents.epoch, values.x, values.y, values.z]
        self.check_and_write_data()

    def acc_data_handler(self, ctx, data):
        values = parse_value(data)
        self.acc_data = [data.contents.epoch, values.x, values.y, values.z]
        self.check_and_write_data()

    def mag_data_handler(self, ctx, data):
        values = parse_value(data)
        self.mag_data = [data.contents.epoch, values.x, values.y, values.z]
        self.check_and_write_data()

    def check_and_write_data(self):
        if self.gyro_data and self.acc_data and self.mag_data:
            with lock:
                row = [self.samples, self.index] + self.gyro_data + self.acc_data[1:] + self.mag_data[1:]
                data_queue.put(row)
                self.samples += 1
            self.gyro_data = None
            self.acc_data = None
            self.mag_data = None

def writer_thread_function():
    with open('sensor_data.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        fieldnames = ['sample_count', 'sensor_index', 'epoch', 'gyro_x', 'gyro_y', 'gyro_z',
                      'accel_x', 'accel_y', 'accel_z', 'mag_x', 'mag_y', 'mag_z']
        writer.writerow(fieldnames)

        while not stop_event.is_set() or not data_queue.empty():
            if not data_queue.empty():
                row = data_queue.get()
                with lock:
                    writer.writerow(row)
                data_queue.task_done()

def configure_sensors(states):
    for s in states:
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(s.device.board, 7.5, 7.5, 0, 6000)
        sleep(2)

        print("Configuring gyro and acc")  # Updated message
        libmetawear.mbl_mw_gyro_bmi270_set_range(s.device.board, GyroBoschRange._1000dps)
        libmetawear.mbl_mw_gyro_bmi270_set_odr(s.device.board, GyroBoschOdr._25Hz)
        libmetawear.mbl_mw_gyro_bmi270_write_config(s.device.board)
        libmetawear.mbl_mw_acc_bmi270_set_odr(s.device.board, AccBmi270Odr._25Hz)
        libmetawear.mbl_mw_acc_bosch_set_range(s.device.board, AccBoschRange._4G)
        libmetawear.mbl_mw_acc_write_acceleration_config(s.device.board)
        libmetawear.mbl_mw_mag_bmm150_set_preset(s.device.board, MagBmm150Preset.HIGH_ACCURACY)
        libmetawear.mbl_mw_mag_bmm150_configure(s.device.board, 9, 15, 6)
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(s.device.board)
        sleep(1)

        print("Packed signal")
        gyro = libmetawear.mbl_mw_gyro_bmi270_get_packed_rotation_data_signal(s.device.board)
        acc = libmetawear.mbl_mw_acc_get_packed_acceleration_data_signal(s.device.board)
        mag = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(s.device.board)

        libmetawear.mbl_mw_datasignal_subscribe(gyro, None, s.callbacks['gyro'])
        libmetawear.mbl_mw_datasignal_subscribe(acc, None, s.callbacks['acc'])
        libmetawear.mbl_mw_datasignal_subscribe(mag, None, s.callbacks['mag'])
        sleep(1)

def start_streaming(states):
    for s in states:
        print("Start")
        libmetawear.mbl_mw_gyro_bmi270_enable_rotation_sampling(s.device.board)
        libmetawear.mbl_mw_gyro_bmi270_start(s.device.board)
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(s.device.board)
        libmetawear.mbl_mw_acc_start(s.device.board)
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(s.device.board)
        libmetawear.mbl_mw_mag_bmm150_start(s.device.board)
        sleep(1)

def stop_and_disconnect(states):
    for s in states:
        libmetawear.mbl_mw_gyro_bmi270_stop(s.device.board)
        libmetawear.mbl_mw_gyro_bmi270_disable_rotation_sampling(s.device.board)
        libmetawear.mbl_mw_acc_stop(s.device.board)
        libmetawear.mbl_mw_acc_disable_acceleration_sampling(s.device.board)
        libmetawear.mbl_mw_mag_bmm150_stop(s.device.board)
        libmetawear.mbl_mw_mag_bmm150_disable_b_field_sampling(s.device.board)
        sleep(1)

        gyro = libmetawear.mbl_mw_gyro_bmi270_get_packed_rotation_data_signal(s.device.board)
        acc = libmetawear.mbl_mw_acc_get_packed_acceleration_data_signal(s.device.board)
        mag = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(s.device.board)

        libmetawear.mbl_mw_datasignal_unsubscribe(gyro)
        libmetawear.mbl_mw_datasignal_unsubscribe(acc)
        libmetawear.mbl_mw_datasignal_unsubscribe(mag)

        libmetawear.mbl_mw_debug_disconnect(s.device.board)
        sleep(1)

stop_event = Event()
lock = Lock()
data_queue = Queue()

states = []

writer_thread = Thread(target=writer_thread_function)
writer_thread.start()

for i in range(len(sys.argv) - 1):
    d = MetaWear(sys.argv[i + 1])
    d.connect()
    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    states.append(State(d, i))

configure_sensors(states)
start_streaming(states)

sleep(10.0)

stop_and_disconnect(states)

stop_event.set()
writer_thread.join()

print("Total Samples Received")
for s in states:
    print("%s -> %d" % (s.device.address, s.samples))
