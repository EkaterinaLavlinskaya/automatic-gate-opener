import cv2
import easyocr
from ultralytics import YOLO

# Загружаем модель YOLO для номеров
model = YOLO('yolov8n.pt')  # или путь к твоей модели

reader = easyocr.Reader(['ru', 'en'])

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Детекция номеров
    results = model(frame)
    
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2 = map(int, box)
            plate_img = frame[y1:y2, x1:x2]
            
            # OCR на вырезанной области
            ocr_result = reader.readtext(plate_img)
            if ocr_result:
                plate_text = ocr_result[0][1]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, plate_text, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow("License Plate Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
