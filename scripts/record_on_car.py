import cv2
import numpy as np
import os
import datetime

# НАСТРОЙКИ
YOLO_PATH = r"C:\MyPythonProjects\AV\yolo-coco"
OUTPUT_FOLDER = r"C:\MyPythonProjects\AV"  # куда сохранять видео
CONFIDENCE_THRESHOLD = 0.5
TARGET_IDS = [2, 5, 7, 6]  # car, bus, truck

#ЗАГРУЗКА YOLO
print("Загрузка YOLO...")
with open(os.path.join(YOLO_PATH, "coco.names"), "r") as f:
    classes = [line.strip() for line in f.readlines()]

net = cv2.dnn.readNet(
    os.path.join(YOLO_PATH, "yolov3.weights"),
    os.path.join(YOLO_PATH, "yolov3.cfg")
)

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# КАМЕРА 
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print(" Камера не найдена")
    exit()

# ПЕРЕМЕННЫЕ ДЛЯ ЗАПИСИ
recording = False
out = None
filename = ""

print(" Слежу за машинами... Нажми 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    height, width = frame.shape[:2]

    # Детекция YOLO (уменьшенный размер для скорости)
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (320, 320), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)

    car_detected = False

    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > CONFIDENCE_THRESHOLD and class_id in TARGET_IDS:
                car_detected = True
                
                # Рисуем рамку
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = center_x - w // 2
                y = center_y - h // 2
                
                label = f"{classes[class_id]}: {confidence:.2f}"
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # ЛОГИКА ЗАПИСИ
    if car_detected:
        if not recording:
            # Начинаем запись
            filename = os.path.join(OUTPUT_FOLDER, f"car_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
            recording = True
            print(f"🎬 МАШИНА! Запись начата: {filename}")
    else:
        if recording:
            # Останавливаем запись
            recording = False
            out.release()
            print(f" Запись остановлена")

    # Записываем кадр, если идет запись
    if recording:
        # Добавляем таймстамп
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        out.write(frame)

    # Показываем статус на экране
    status = "REC" if recording else "WAIT"
    cv2.putText(frame, status, (width - 60, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if recording else (0, 255, 0), 2)
    
    cv2.imshow("Car Detection & Recording", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

#  ЗАВЕРШЕНИЕ
if recording:
    out.release()
cap.release()
cv2.destroyAllWindows()
print(" Программа завершена")
