from __future__ import print_function
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event, Thread, Lock, RLock
from collections import deque
import sys
import time

class State:
    def __init__(self, device, states):
        self.device = device
        self.samples = 0
        self.latest_data = None
        self.states = states  # Referencia a todos los estados de los sensores
        self.callback = FnVoid_VoidP_DataP(self.data_handler)

    def data_handler(self, ctx, data):
        # Parsear el valor recibido
        parsed_data = parse_value(data)
        self.latest_data = parsed_data
        self.samples += 1  # Contar el número de muestras recibidas

        # Imprimir el buffer combinado actualizado
        self.combined_bufferA()

    def combined_bufferA(self):
        # Crear un buffer combinado con los datos más recientes de cada sensor
        bufferA = []
        for state in self.states:
            if state.latest_data:
                bufferA.extend([state.latest_data.w, state.latest_data.x, state.latest_data.y, state.latest_data.z])
                # bufferA.extend([state.latest_data.timestamp, state.latest_data.w, state.latest_data.x, state.latest_data.y, state.latest_data.z])
            else:
                bufferA.extend([None, None, None, None])  # Si no hay datos, se colocan None
            # else:
            #     bufferA.extend([None, None, None, None, None])  # Si no hay datos, se colocan None

        # Imprimir el buffer combinado
        print("Combined Buffer:")
        print(bufferA)

def connect_and_configure_sensors(device_addresses):
    states = []
    for address in device_addresses:
        d = MetaWear(address)
        d.connect()
        print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
        states.append(State(d, states))  # Pasar referencia de todos los estados

    for s in states:
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(s.device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        libmetawear.mbl_mw_sensor_fusion_set_mode(s.device.board, SensorFusionMode.NDOF)
        libmetawear.mbl_mw_sensor_fusion_set_acc_range(s.device.board, SensorFusionAccRange._8G)
        libmetawear.mbl_mw_sensor_fusion_set_gyro_range(s.device.board, SensorFusionGyroRange._2000DPS)
        libmetawear.mbl_mw_sensor_fusion_write_config(s.device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(s.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_datasignal_subscribe(signal, None, s.callback)
        libmetawear.mbl_mw_sensor_fusion_enable_data(s.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_sensor_fusion_start(s.device.board)

    return states

def disconnect_sensors(states):
    for s in states:
        libmetawear.mbl_mw_sensor_fusion_stop(s.device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(s.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)
        libmetawear.mbl_mw_debug_disconnect(s.device.board)
        print("Disconnected from " + s.device.address)

def main():
    device_addresses = sys.argv[1:]
    states = connect_and_configure_sensors(device_addresses)
    try:
        print("Streaming data. Press CTRL+C to stop.")
        while True:
            sleep(1)  # Mantén el script en ejecución para recibir datos
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        disconnect_sensors(states)
        print("All sensors disconnected.")

if __name__ == "__main__":
    main()

