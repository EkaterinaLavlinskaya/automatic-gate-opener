import cv2
import numpy as np
import os

# Загрузка классов
with open("yolo-coco/coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Индексы интересующих классов
TARGET_CLASSES = {"car": 2, "truck": 7, "bus": 5}  # в coco.names car под номером 2
TARGET_IDS = list(TARGET_CLASSES.values())

# Загрузка YOLO
net = cv2.dnn.readNet("yolo-coco/yolov3.weights", "yolo-coco/yolov3.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# Открываем камеру
cap = cv2.VideoCapture(0)

print("Распознавание машин... Нажми 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    height, width = frame.shape[:2]
    
    # Подготовка для YOLO
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)
    
    boxes, confidences, class_ids = [], [], []
    
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            # Фильтруем только машины (car, truck, bus)
            if confidence > 0.5 and class_id in TARGET_IDS:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = center_x - w // 2
                y = center_y - h // 2
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)
    
    # Убираем дублирующиеся рамки
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    
    # Рисуем результат
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = f"{classes[class_ids[i]]}: {confidences[i]:.2f}"
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    cv2.imshow("Car Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
