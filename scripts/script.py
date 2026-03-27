import cv2
import numpy as np
import datetime
import os

# ===== НАСТРОЙКИ =====
YOLO_PATH = r"C:\MyPythonProjects\AV\yolo-coco"
OUTPUT_FOLDER = r"C:\Users\Денис\Downloads"
CONFIDENCE_THRESHOLD = 0.6  # Увеличил с 0.5 до 0.6
TARGET_IDS = [2, 5, 7]  # car, bus, truck

# ===== ЗАГРУЗКА YOLO =====
with open(os.path.join(YOLO_PATH, "coco.names"), "r") as f:
    classes = [line.strip() for line in f.readlines()]

net = cv2.dnn.readNet(
    os.path.join(YOLO_PATH, "yolov3.weights"),
    os.path.join(YOLO_PATH, "yolov3.cfg")
)

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# ===== КАМЕРА =====
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Камера не найдена")
    exit()

recording = False
out = None
no_car_counter = 0  # счетчик кадров без машины
MIN_CAR_FRAMES = 3  # сколько кадров подряд должна быть машина для старта записи
car_detection_history = []  # история обнаружений

print("🔍 Слежу за машинами... Нажми 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    height, width = frame.shape[:2]

    # YOLO детекция
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (320, 320), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)

    car_detected = False
    best_confidence = 0
    best_box = None

    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > CONFIDENCE_THRESHOLD and class_id in TARGET_IDS:
                car_detected = True
                if confidence > best_confidence:
                    best_confidence = confidence
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = center_x - w // 2
                    y = center_y - h // 2
                    best_box = (x, y, w, h)

    # Рисуем рамку, если есть
    if best_box:
        x, y, w, h = best_box
        label = f"car: {best_confidence:.2f}"
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # ===== УМНАЯ ЗАПИСЬ (с историей) =====
    car_detection_history.append(car_detected)
    if len(car_detection_history) > MIN_CAR_FRAMES:
        car_detection_history.pop(0)

    # Запись начинается, если в последних N кадрах была машина
    stable_car_detected = sum(car_detection_history) >= MIN_CAR_FRAMES

    if stable_car_detected:
        if not recording:
            filename = os.path.join(OUTPUT_FOLDER, f"car_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
            recording = True
            print(f"🎬 МАШИНА! Запись: {filename}")
    else:
        if recording:
            recording = False
            out.release()
            print(f"⏹️ Запись остановлена")

    if recording:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "REC", (width - 60, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        out.write(frame)

    # Статус
    status = "DETECTED" if car_detected else "WAIT"
    cv2.putText(frame, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if car_detected else (0, 0, 255), 2)

    cv2.imshow("Car Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if recording:
    out.release()
cap.release()
cv2.destroyAllWindows()
print("✅ Программа завершена")
