"""
Управление светодиодом (симуляция ворот) через Arduino.
Команды: '1' — включить, '0' — выключить
"""

import serial
import time

def connect_arduino(port='COM4', baudrate=9600):
    """Подключение к Arduino"""
    try:
        arduino = serial.Serial(port, baudrate)
        time.sleep(2)   # ждём инициализации
        print(f"Подключено к {port}")
        return arduino
    except Exception as e:
        print(f" Ошибка подключения: {e}")
        return None

def open_gate(arduino, recognized_text, allowed_plates):
    """Открыть ворота, если номер в списке"""
    if recognized_text in allowed_plates:
        arduino.write(b'1')
        print("Ворота открыты")
        return True
    else:
        print("Номер не в списке. Ворота закрыты")
        return False

def close_gate(arduino):
    """Закрыть ворота (выключить светодиод)"""
    arduino.write(b'0')
    print(" Ворота закрыты")

if __name__ == "__main__":

    PORT = 'COM4'   


    arduino = connect_arduino(PORT)
    if arduino:
        open_gate(arduino)
        time.sleep(2)
        close_gate(arduino)
        arduino.close()
