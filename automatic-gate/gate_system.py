import cv2
import easyocr
import serial
import time
import re
import datetime
import os
import requests
from ultralytics import YOLO

# ============================================
# НАСТРОЙКИ
# ============================================
try:
    arduino = serial.Serial('COM4', 9600, timeout=1)
    time.sleep(2)
    print("✅ Arduino подключён")
except:
    arduino = None
    print("⚠️ Arduino не найден, работаем без него")

# SMS (опционально)
SMS_API_KEY = "ВАШ_API_КЛЮЧ"
YOUR_PHONE = "+7XXXXXXXXXX"

# База разрешённых номеров
ALLOWED_PLATES = {"А273КК", "Н642ВУ"}

# Папка для видео
VIDEO_SAVE_PATH = "recordings"
if not os.path.exists(VIDEO_SAVE_PATH):
    os.makedirs(VIDEO_SAVE_PATH)

# Загрузка моделей
model = YOLO("yolo11n.pt")
reader = easyocr.Reader(['ru', 'en'], gpu=False)

# Переменные для записи
recording = False
video_writer = None
current_recording_start = None
last_car_detected_time = 0
NO_CAR_TIMEOUT = 3
car_detected = False

# ============================================
# ФУНКЦИИ
# ============================================
def normalize_plate(text):
    lat_to_cyr = {
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
        'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
        'X': 'Х', 'Y': 'У'
    }
    for lat, cyr in lat_to_cyr.items():
        text = text.replace(lat, cyr)
    
    text = re.sub(r'[^А-Я0-9]', '', text.upper())
    
    for i, ch in enumerate(text):
        if ch.isalpha():
            text = text[i:]
            break
    
    if len(text) > 6:
        text = text[:6]
    return text

def add_timestamp(frame):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, current_time, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

def send_sms(message):
    if SMS_API_KEY and YOUR_PHONE:
        try:
            url = "https://sms.ru/sms/send"
            params = {"api_id": SMS_API_KEY, "to": YOUR_PHONE, "msg": message, "json": 1}
            requests.get(url, params=params)
            print(f"📱 SMS: {message[:50]}...")
        except:
            pass

# ============================================
# ОСНОВНОЙ ЦИКЛ
# ============================================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Не удалось открыть камеру")
    exit()

print("✅ Камера запущена. Нажми 'q' для выхода")
print("📹 Запись MP4 начнётся при обнаружении автомобиля")
print("🔍 Распознавание номеров включено")

frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = add_timestamp(frame)
    frame_count += 1
    
    if frame_count % 3 == 0:
        results = model(frame, conf=0.3)
        cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]
        
        if cars:
            if not car_detected:
                car_detected = True
                print(f"🚗 Автомобиль обнаружен в {datetime.datetime.now().strftime('%H:%M:%S')}")
                if not recording:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(VIDEO_SAVE_PATH, f"car_{timestamp}.mp4")
                    h, w = frame.shape[:2]
                    # Используем MP4V кодек для MP4
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
                    recording = True
                    current_recording_start = time.time()
                    print(f"🎥 Начата запись: {filename}")
            
            last_car_detected_time = time.time()
            
            for car in cars:
                x1, y1, x2, y2 = map(int, car.xyxy[0].tolist())
                car_h = y2 - y1
                car_w = x2 - x1
                
                y1_plate = y1 + int(car_h * 0.50)
                y2_plate = y1 + int(car_h * 0.92)
                x1_plate = x1 + int(car_w * 0.15)
                x2_plate = x2 - int(car_w * 0.15)
                
                plate = frame[y1_plate:y2_plate, x1_plate:x2_plate]
                
                if plate.size > 0:
                    result = reader.readtext(plate)
                    if result:
                        raw_text = result[0][1].upper()
                        confidence = result[0][2]
                        normalized = normalize_plate(raw_text)
                        
                        print(f"🔍 Распознано: {raw_text} → {normalized} (уверенность: {confidence:.2f})")
                        
                        if normalized in ALLOWED_PLATES:
                            print(f"🔓 ДОСТУП РАЗРЕШЁН! Номер {normalized} в базе")
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, f"GRANTED: {normalized}", (x1, y1-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            if arduino:
                                arduino.write(b'OPEN\n')
                                print("🔌 Команда OPEN отправлена на Arduino")
                        else:
                            print(f"🔒 ДОСТУП ЗАПРЕЩЁН! Номер {normalized} не в базе")
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            cv2.putText(frame, f"DENIED: {normalized}", (x1, y1-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    else:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                        cv2.putText(frame, "Plate?", (x1, y1-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        else:
            if car_detected:
                if time.time() - last_car_detected_time > NO_CAR_TIMEOUT:
                    car_detected = False
                    print(f"🚫 Автомобиль покинул зону в {datetime.datetime.now().strftime('%H:%M:%S')}")
                    if recording and video_writer:
                        video_writer.release()
                        video_writer = None
                        duration = time.time() - current_recording_start
                        print(f"🛑 Запись остановлена (длительность: {duration:.1f} сек)")
                        recording = False
    
    if recording and video_writer:
        video_writer.write(frame)
    
    cv2.imshow("Gate Control", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if video_writer:
    video_writer.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
