import sys
from time import sleep
from threading import Event
from collections import deque
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer
import torch
import torch.nn as nn
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from mbientlab.warble import *

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, num_layers):
        super(LSTMModel, self).__init__()
        self.num_layers = num_layers
        self.hidden_size = hidden_size
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        h_0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c_0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h_0, c_0))
        out = self.fc(out[:, -1, :])
        return out

class SensorState:
    def __init__(self, device):
        self.device = device
        self.quaternion = None
        self.callback = FnVoid_VoidP_DataP(self.data_handler)
        self.buffer = deque(maxlen=100)  # Buffer para almacenar las ultimas 100 muestras (1 segundo de datos a 100Hz)

    def data_handler(self, ctx, data):
        self.quaternion = parse_value(data)
        self.buffer.append([self.quaternion.w, self.quaternion.x, self.quaternion.y, self.quaternion.z])

    def start_stream(self):
        print("Configuring device")
        libmetawear.mbl_mw_settings_set_connection_parameters(self.device.board, 7.5, 7.5, 0, 6000)
        sleep(1.5)
        libmetawear.mbl_mw_sensor_fusion_set_mode(self.device.board, SensorFusionMode.NDOF)
        libmetawear.mbl_mw_sensor_fusion_set_acc_range(self.device.board, SensorFusionAccRange._8G)
        libmetawear.mbl_mw_sensor_fusion_set_gyro_range(self.device.board, SensorFusionGyroRange._2000DPS)
        libmetawear.mbl_mw_sensor_fusion_write_config(self.device.board)
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_datasignal_subscribe(signal, None, self.callback)
        libmetawear.mbl_mw_sensor_fusion_enable_data(self.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_sensor_fusion_start(self.device.board)

    def stop_stream(self):
        signal = libmetawear.mbl_mw_sensor_fusion_get_data_signal(self.device.board, SensorFusionData.QUATERNION)
        libmetawear.mbl_mw_datasignal_unsubscribe(signal)
        libmetawear.mbl_mw_sensor_fusion_stop(self.device.board)

    def disconnect(self):
        libmetawear.mbl_mw_debug_disconnect(self.device.board)
        print("Disconnected")

class App(QWidget):
    def __init__(self, model, sensor1, sensor2):
        super().__init__()
        self.model = model
        self.sensor1 = sensor1
        self.sensor2 = sensor2
        self.initUI()

    def initUI(self):
        self.label = QLabel('Prediction: ', self)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setWindowTitle('Real-Time Arm Position Detection')
        self.setGeometry(100, 100, 400, 200)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_prediction)
        self.timer.start(1000)  # Actualizar cada segundo

        self.show()

    def preprocess_data(self, buffer1, buffer2):
        data = []
        for q1, q2 in zip(buffer1, buffer2):
            data.append(q1 + q2)  # Concatenar los datos quaterniones de los dos sensores
        data = torch.tensor(data, dtype=torch.float32)
        data = data.unsqueeze(0)  # Añadir dimensión batch
        return data

    def update_prediction(self):
        if len(self.sensor1.buffer) == 100 and len(self.sensor2.buffer) == 100:
            data = self.preprocess_data(list(self.sensor1.buffer), list(self.sensor2.buffer))
            with torch.no_grad():
                output = self.model(data)
                probabilities = torch.softmax(output, dim=1)
                prediction = torch.argmax(probabilities, dim=1).item()
                self.label.setText(f'Prediction: {"Arm Up" if prediction == 1 else "Arm Down"}')
                print(f'True: Sensor 1 Buffer: {list(self.sensor1.buffer)}, Sensor 2 Buffer: {list(self.sensor2.buffer)} | Prediction: {"Arm Up" if prediction == 1 else "Arm Down"}')

if __name__ == '__main__':
    # Verificar argumentos de la línea de comandos
    if len(sys.argv) < 3:
        print("Usage: python3 script.py [MAC1] [MAC2]")
        sys.exit(1)

    # Definir los mismos parámetros que se usaron en el entrenamiento
    input_size = 8
    hidden_size = 128
    output_size = 2
    num_layers = 2

    # Cargar el modelo entrenado
    model = LSTMModel(input_size=input_size, hidden_size=hidden_size, output_size=output_size, num_layers=num_layers)
    model.load_state_dict(torch.load('../GUI_CAWT/NNModel/lstm_model.pth'))
    model.eval()

    # Crear y conectar los sensores
    sensor1_device = MetaWear('EE:1B:72:FA:BF:E8')
    sensor2_device = MetaWear('E1:E9:FC:FD:0C:70')
    sensor1_device.connect()
    sensor2_device.connect()

    sensor1 = SensorState(sensor1_device)
    sensor2 = SensorState(sensor2_device)

    sensor1.start_stream()
    sensor2.start_stream()

    # Crear y ejecutar la aplicación
    app = QApplication(sys.argv)
    ex = App(model, sensor1, sensor2)
    sys.exit(app.exec_())

    # Detener los streams y desconectar los sensores
    sensor1.stop_stream()
    sensor2.stop_stream()
    sleep(1.5)
    sensor1.disconnect()
    sensor2.disconnect()
    sleep(1.5)
    print("Sensores Desconectados")
