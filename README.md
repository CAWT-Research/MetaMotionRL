# **CAWT Streaming Data with MetaMotionRL**

## This repository is composed of 5 parts:

1. [Streaming](https://github.com/CAWT-Research/MetaMotionRL/tree/main/Streaming) :watch:: Codes to generate the streaming of the data coming from the MbientLAB MetaMotionRL sensors in general, there are also some examples of interruptions via timer using python.
2. [DataCollection](https://github.com/CAWT-Research/MetaMotionRL/tree/main/DataCollection) :bar_chart:: Datos recogidos para en entrenamiento de la red neuronal simple, en los codigo encontrados en la carpeta No. 3 se encuentran los codigos para recolectar datos, según sea la necesidad
3. [GUI_Developer](https://github.com/CAWT-Research/MetaMotionRL/tree/main/GUI_Developer) :computer:: Simple GUI to view the behavior of the data in a simple graphical interface, there are several examples, to view the accelerations, gyroscope and magnetometer independently in its three axes, or the three components in a single code with each of its axes. Also the sensor_fusion to obtain the data of the quaternions or euler angles.
4. [GUI_Final](https://github.com/CAWT-Research/MetaMotionRL/tree/main/GUI_Final) :computer:: GUI that integrates all the development, i.e. data streaming and prediction of the neural network, as well as a graph with the behavior of the data.
5. [NNModel](https://github.com/CAWT-Research/MetaMotionRL/tree/main/NNModel) :file_folder:: Code to test the neural network independently with streaming data in a simple graphical interface that shows the prediction made by the network.

This repository contains each of the parts developed independently and integrated to make a prediction about the movement of a person's arm (Up or Down).
