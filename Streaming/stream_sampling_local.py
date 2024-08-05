from __future__ import print_function
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event, Thread, Lock, RLock
from collections import deque
import sys
import time

class State:
    def __init__(self, device):
        self.device = device
        # self.samples = 0
        self.data_buffer = deque(maxlen=100)  # Buffer circular para los últimos 100 datos
        self.lock = RLock()                    # Para proteger el acceso al buffer
        self.callback = FnVoid_VoidP_DataP(self.data_handler)

    def data_handler(self, ctx, data):
        # Inspección de `data` antes de procesarlo
        # print(f"Raw data received from {self.device.address}: {data}")

        # Intento de parsear el valor
        parsed_data = parse_value(data)
        
        # Verificar si `parsed_data` tiene los atributos correctos
        # print(parsed_data)
        print(f"Parsed data from {self.device.address}: w={parsed_data.w}, x={parsed_data.x}, y={parsed_data.y}, z={parsed_data.z}\n")
        
        # Comprobar si los valores son cero antes de continuar
        if parsed_data.w <= 0 and parsed_data.x <= 0 and parsed_data.y <= 0 and parsed_data.z <= 0:
            print("Warning: All parsed data values are zero. This might indicate an issue with the parsing function or incoming data.")
        
        # self.samples += 1
        with self.lock:
            # Asegurarse de que cada dato sea independiente
            self.data_buffer.append(parsed_data)
            # print(f"Buffer updated for {self.device.address}: {(self.data_buffer)[0]}")
            # print("__________________________________________________________________")

            # latest = (self.data_buffer)[0]
            # print(f"Saved latest data from {self.device.address}: {latest}")

            print(" \n \n \n SAVE\n")
            print(self.data_buffer)
            print("\n \n \n")

            print(f"size queue {len(self.data_buffer)}")

#GARANTIZAR QUE LOS DATOS SE ESTEN LLENANDO CORRECTAMENTE EN EL BUFFER
    def get_latest_data(self):
        with self.lock:
            if self.data_buffer:
                # latest = (self.data_buffer)
                # print("\n \n \nACCESS\n")
                # print(self.data_buffer)
                # print("\n \n \n")
                #print(f"Accessing latest data from {self.device.address}: {latest}")
                return latest
            else:
                print(f"No data available in buffer for {self.device.address}")
            return None

# Conectar a los dispositivos
states = []
for i in range(len(sys.argv) - 1):
    d = MetaWear(sys.argv[i + 1])
    d.connect()
    print("Connected to " + d.address + " over " + ("USB" if d.usb.is_connected else "BLE"))
    states.append(State(d))

# Configurar dispositivos
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

# Función para procesar los datos cada 10 ms
def process_data():
    while not stop_event.is_set():
        try:
            for state in states:
                latest_data = state.get_latest_data()
                if latest_data is not None:
                    print()
                    # print(f"Latest data from {state.device.address}: {latest_data}")
                else:
                    # print(f"No data available for {state.device.address}")
                    print()
        except Exception as e:
            print(f"Error in processing data: {e}")
        time.sleep(0.01)  # Espera 10 ms

# Iniciar hilo de procesamiento de datos
stop_event = Event()
processing_thread = Thread(target=process_data)
processing_thread.start()

# Esperar durante el streaming (por ejemplo, 10 segundos)
sleep(0.5)

# Parar procesamiento de datos
stop_event.set()
processing_thread.join()

# Detener y desconectar los dispositivos
for s in states:
    libmetawear.mbl_mw_sensor_fusion_stop(s.device.board)
    signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(s.device.board, SensorFusionData.QUATERNION)
    libmetawear.mbl_mw_datasignal_unsubscribe(signal)
    libmetawear.mbl_mw_debug_disconnect(s.device.board)

# print("Total Samples Received")
# for s in states:
#     print("%s -> %d" % (s.device.address, s.samples))
