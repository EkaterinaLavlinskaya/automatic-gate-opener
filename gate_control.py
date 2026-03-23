import serial
import time

arduino = serial.Serial('COM4', 9600)   
time.sleep(2)                           # ждём инициализации

# Открыть ворота (зажечь светодиод)
arduino.write(b'1')
time.sleep(2)

# Закрыть ворота (погасить)
arduino.write(b'0')
arduino.close()

import cv2
import easyocr

reader = easyocr.Reader(['ru', 'en'])
img = cv2.imread('car_with_plate.jpg')
plate = img[100:200, 150:350]   # подобрать координаты под своё фото
result = reader.readtext(plate)
print(result)   # [([[x1,y1,x2,y2]], 'A123BC', confidence)]

allowed_plates = ['A123BC', 'B456DE']

recognized_text = result[0][1]   # текст номера

if recognized_text in allowed_plates:
    arduino.write(b'1')          # открываем ворота
else:
    print("Номер не в списке")
