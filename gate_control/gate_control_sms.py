import cv2
import easyocr
import serial
import time
import re
import datetime
import os
import requests
import threading
from ultralytics import YOLO

# ============================================
# НАСТРОЙКИ SMS (SMS.ru)
# ============================================
# Зарегистрируйся на sms.ru, получи API ключ
SMS_API_KEY = "ВАШ_API_КЛЮЧ"  # из личного кабинета sms.ru
SMS_FROM = "ВАШ_НОМЕР_ОТПРАВИТЕЛЯ"  # обычно не нужно, можно оставить пустым
YOUR_PHONE = "+7XXXXXXXXXX"  #  номер для уведомлений

# Состояние ожидания ответа на SMS
waiting_for_sms_reply = False
pending_plate_number = None
pending_plate_timestamp = None

# ============================================
# НАСТРОЙКИ ARDUINO
# ============================================
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
    print("✅ Arduino подключён")
except:
    arduino = None
    print("⚠️ Arduino не найден, работаем без него")

# ============================================
# НАСТРОЙКИ БАЗЫ НОМЕРОВ
# ============================================
ALLOWED_PLATES = {"А273КК", "Н642ВУ"}

# ============================================
# НАСТРОЙКИ ВИДЕОЗАПИСИ
# ============================================
VIDEO_SAVE_PATH = "recordings"
if not os.path.exists(VIDEO_SAVE_PATH):
    os.makedirs(VIDEO_SAVE_PATH)

# ============================================
# ЗАГРУЗКА МОДЕЛЕЙ
# ============================================
model = YOLO("yolo11n.pt")
reader = easyocr.Reader(['ru', 'en'], gpu=False)

# ============================================
# ПЕРЕМЕННЫЕ ДЛЯ ЗАПИСИ ВИДЕО
# ============================================
recording = False
video_writer = None
current_recording_start = None
last_car_detected_time = 0
NO_CAR_TIMEOUT = 3

# ============================================
# ФУНКЦИИ SMS
# ============================================
def send_sms(phone, message):
    """Отправка SMS через SMS.ru"""
    try:
        url = "https://sms.ru/sms/send"
        params = {
            "api_id": SMS_API_KEY,
            "to": phone,
            "msg": message,
            "json": 1
        }
        if SMS_FROM:
            params["from"] = SMS_FROM
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK":
            print(f"📱 SMS отправлено на {phone}: {message[:50]}...")
            return True
        else:
            print(f"❌ Ошибка SMS: {data}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки SMS: {e}")
        return False

def open_gate():
    """Открывает ворота"""
    if arduino:
        arduino.write(b'OPEN\n')
        print(f"🔓 Ворота открыты в {datetime.datetime.now().strftime('%H:%M:%S')}")
        # Отправляем уведомление об открытии
        send_sms(YOUR_PHONE, "🔓 Ворота открыты")
    else:
        print("⚠️ Arduino не подключён")

def close_gate():
    """Закрывает ворота (если нужно)"""
    if arduino:
        arduino.write(b'CLOSE\n')
        print(f"🔒 Ворота закрыты в {datetime.datetime.now().strftime('%H:%M:%S')}")
        send_sms(YOUR_PHONE, "🔒 Ворота закрыты")

def request_access_for_plate(plate_number):
    """Запрашивает у владельца разрешение на открытие"""
    global waiting_for_sms_reply, pending_plate_number, pending_plate_timestamp
    
    waiting_for_sms_reply = True
    pending_plate_number = plate_number
    pending_plate_timestamp = time.time()
    
    message = f"🚗 Машина с номером {plate_number} подъехала. Нет в базе. Открыть ворота?\n1 - Да\n0 - Нет"
    send_sms(YOUR_PHONE, message)

def check_sms_reply():
    """Проверяет, не пришёл ли ответ на SMS (имитация)"""
    global waiting_for_sms_reply, pending_plate_number
    
    # В реальной системе нужно настроить webhook или polling
    # Для демонстрации используем ручной ввод в консоли
    if waiting_for_sms_reply:
        print(f"\n📱 Ожидание ответа для номера {pending_plate_number}")
        print("Введите 1 (открыть) или 0 (отказать):")
        user_input = input().strip()
        
        if user_input == "1":
            print(f"✅ Разрешено открытие для {pending_plate_number}")
            open_gate()
            # Добавляем номер в базу (опционально)
            # ALLOWED_PLATES.add(pending_plate_number)
        else:
            print(f"❌ Отказано в доступе для {pending_plate_number}")
            send_sms(YOUR_PHONE, f"❌ Доступ запрещён для {pending_plate_number}")
        
        waiting_for_sms_reply = False
        pending_plate_number = None

# ============================================
# ФУНКЦИИ ВИДЕОЗАПИСИ
# ============================================
def start_recording(frame):
    global recording, video_writer, current_recording_start
    if recording:
        return
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(VIDEO_SAVE_PATH, f"car_{timestamp}.avi")
    h, w = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
    recording = True
    current_recording_start = time.time()
    print(f"🎥 Начата запись: {filename}")

def stop_recording():
    global recording, video_writer, current_recording_start
    if not recording:
        return
    if video_writer:
        video_writer.release()
        video_writer = None
    duration = time.time() - current_recording_start if current_recording_start else 0
    recording = False
    print(f"🛑 Запись остановлена (длительность: {duration:.1f} сек)")

def add_timestamp(frame):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, current_time, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

# ============================================
# НОРМАЛИЗАЦИЯ НОМЕРА
# ============================================
def normalize_plate(text):
    """Приводит распознанный текст к формату А123БВ"""
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
    
    if len(text) >= 6:
        result = []
        
        if text[0].isdigit():
            digit_to_letter = {'0': 'О', '1': 'Р', '2': 'З', '3': 'Е', '4': 'Ч',
                               '5': 'С', '6': 'Б', '7': 'Т', '8': 'В', '9': 'У'}
            result.append(digit_to_letter.get(text[0], 'А'))
        else:
            result.append(text[0])
        
        digits_count = 0
        for i in range(1, min(4, len(text))):
            ch = text[i]
            if ch.isdigit():
                result.append(ch)
                digits_count += 1
            elif ch in 'ЗЕОСВ':
                letter_to_digit = {'З': '3', 'Е': '3', 'О': '0', 'С': '5', 'В': '8'}
                result.append(letter_to_digit.get(ch, '0'))
                digits_count += 1
            else:
                result.append('0')
                digits_count += 1
        
        while digits_count < 3:
            result.append('0')
            digits_count += 1
        
        letters_count = 0
        for i in range(4, min(6, len(text))):
            ch = text[i]
            if ch.isalpha():
                result.append(ch)
                letters_count += 1
            elif ch.isdigit():
                digit_to_letter = {'0': 'О', '1': 'Р', '2': 'З', '3': 'Е', '4': 'Ч',
                                   '5': 'С', '6': 'Б', '7': 'Т', '8': 'В', '9': 'У'}
                result.append(digit_to_letter.get(ch, 'А'))
                letters_count += 1
            else:
                result.append('А')
                letters_count += 1
        
        while letters_count < 2:
            result.append('А')
            letters_count += 1
        
        text = ''.join(result[:6])
    
    return text

# ============================================
# ОСНОВНОЙ ЦИКЛ
# ============================================
def main():
    global recording, last_car_detected_time, waiting_for_sms_reply
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Не удалось открыть камеру")
        return
    
    print("✅ Камера запущена. Нажми 'q' для выхода")
    print("📝 Запись начнётся при обнаружении автомобиля")
    print("📱 SMS-уведомления включены")
    
    frame_count = 0
    car_detected = False
    last_plate_sent = ""
    last_plate_sent_time = 0
    SEND_SMS_COOLDOWN = 30  # не отправлять SMS чаще чем раз в 30 секунд
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        frame = add_timestamp(frame)
        
        # Проверяем ответ на SMS (в отдельном потоке)
        if waiting_for_sms_reply:
            check_sms_reply()
        
        if frame_count % 3 == 0:
            results = model(frame, conf=0.3)
            cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]
            
            if cars:
                if not car_detected:
                    car_detected = True
                    print(f"🚗 Автомобиль обнаружен в {datetime.datetime.now().strftime('%H:%M:%S')}")
                    start_recording(frame)
                
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
                            
                            print(f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')} | "
                                  f"{raw_text} → {normalized} (conf: {confidence:.2f})")
                            
                            if normalized in ALLOWED_PLATES:
                                print(f"🔓 ДОСТУП РАЗРЕШЁН! {normalized} в базе")
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, f"GRANTED: {normalized}", (x1, y1-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                
                                if arduino:
                                    arduino.write(b'OPEN\n')
                                    send_sms(YOUR_PHONE, f"✅ Доступ разрешён. Номер {normalized} в базе")
                            else:
                                print(f"🔒 ДОСТУП ЗАПРЕЩЁН! {normalized} не в базе")
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                cv2.putText(frame, f"DENIED: {normalized}", (x1, y1-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                                
                                # Отправляем SMS, если не отправляли недавно для этого номера
                                current_time = time.time()
                                if (normalized != last_plate_sent or 
                                    current_time - last_plate_sent_time > SEND_SMS_COOLDOWN):
                                    if not waiting_for_sms_reply:
                                        last_plate_sent = normalized
                                        last_plate_sent_time = current_time
                                        request_access_for_plate(normalized)
            else:
                if car_detected:
                    if time.time() - last_car_detected_time > NO_CAR_TIMEOUT:
                        car_detected = False
                        print(f"🚫 Автомобиль покинул зону в {datetime.datetime.now().strftime('%H:%M:%S')}")
                        stop_recording()
        
        if recording and video_writer:
            video_writer.write(frame)
        
        cv2.imshow("Gate Control", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            if recording:
                stop_recording()
            break
        elif key == ord('r') and not recording:
            start_recording(frame)
        elif key == ord('s') and recording:
            stop_recording()
    
    cap.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()

if __name__ == "__main__":
    main()
