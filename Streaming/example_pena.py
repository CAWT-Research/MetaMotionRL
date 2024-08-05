import time
import threading
from datetime import datetime

def saveData():
    print(f"Time: {datetime.now()}")

def hilo_principal():
    # global finish
    while True:
        timer = threading.Timer(0.1,saveData)
        timer.start()
        timer.join()
        # if(finish == True):
        #     break

t = threading.Thread(target=hilo_principal)
t.start()

try:
    while True:
        # Código principal de la aplicación aquí
        time.sleep(1)  # Para mantener viva la ejecución del hilo principal
except KeyboardInterrupt:
    # Detener el temporizador cuando el usuario presione Ctrl+C
    signal.setitimer(signal.ITIMER_REAL, 0)
    print("Temporizador detenido")