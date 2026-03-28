import cv2
import easyocr
import numpy as np
import ssl

# Отключаем проверку SSL (только для скачивания моделей)
ssl._create_default_https_context = ssl._create_unverified_context

# Инициализируем OCR
print("Загружаем EasyOCR...")
reader = easyocr.Reader(['ru', 'en'], gpu=False)

def find_license_plate_contour(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    best_rect = None
    max_area = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / h
        if 1.5 < aspect_ratio < 5 and area > max_area:
            max_area = area
            best_rect = (x, y, w, h)
    return best_rect

cap = cv2.VideoCapture(0)

print("🔍 Распознавание номеров. Нажми 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    plate_rect = find_license_plate_contour(frame)
    
    if plate_rect:
        x, y, w, h = plate_rect
        plate_img = frame[y:y+h, x:x+w]
        plate_img = cv2.resize(plate_img, (w*2, h*2))
        
        ocr_result = reader.readtext(plate_img)
        
        if ocr_result:
            plate_text = ocr_result[0][1]
            plate_text = ''.join(c for c in plate_text if c.isalnum() or c in 'АВЕКМНОРСТУХ')
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, plate_text, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            print(f"Номер: {plate_text}")
    
    cv2.imshow("License Plate Detection", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Завершено")
