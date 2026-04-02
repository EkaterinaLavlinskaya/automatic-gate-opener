mport cv2
import easyocr
import serial
import time
import re
import datetime
import os
import requests
import pandas as pd
from ultralytics import YOLO

# ============================================
# НАСТРОЙКИ
# ============================================
# Arduino (проверь COM-порт!)
try:
    arduino = serial.Serial('COM4', 9600, timeout=1)
    time.sleep(2)
    print("✅ Arduino подключён")
except:
    arduino = None
    print("⚠️ Arduino не найден, работаем без него")

# SMS (зарегистрируйся на sms.ru)
SMS_API_KEY = "ВАШ_API_КЛЮЧ"  # из личного кабинета sms.ru
YOUR_PHONE = "+7XXXXXXXXXX"   #  номер телефона
SMS_ENABLED = False  # поставь True, если настроил SMS

# Папка для видео
VIDEO_SAVE_PATH = "recordings"
if not os.path.exists(VIDEO_SAVE_PATH):
    os.makedirs(VIDEO_SAVE_PATH)

# ============================================
# БАЗА РАЗРЕШЁННЫХ НОМЕРОВ
# ============================================
ALLOWED_PLATES = ["А273КК", "Н642ВУ", "А123ВС", "В456CD", "X999XX", "К777АА"]

# Сохраняем в CSV
db_path = "allowed_plates.csv"
df = pd.DataFrame({"plate": ALLOWED_PLATES})
df.to_csv(db_path, index=False, encoding="utf-8")
print("✅ База номеров создана")
print("Разрешённые номера:")
for plate in ALLOWED_PLATES:
    print(f"   - {plate}")

# ============================================
# ЗАГРУЗКА МОДЕЛЕЙ
# ============================================
print("Загрузка YOLO...")
model = YOLO("yolo11n.pt")
print("✅ YOLO загружен")

print("Загрузка EasyOCR...")
reader = easyocr.Reader(['ru', 'en'], gpu=False)
print("✅ EasyOCR загружен")

# ============================================
# ПЕРЕМЕННЫЕ ДЛЯ ЗАПИСИ ВИДЕО
# ============================================
recording = False
video_writer = None
recording_start_time = 0
last_car_detected_time = 0
NO_CAR_TIMEOUT = 3  # секунд без машины до остановки записи
car_detected = False
sms_sent_for_current_car = False

# ============================================
# ФУНКЦИЯ ОТПРАВКИ SMS
# ============================================
def send_sms(message):
    """Отправка SMS через SMS.ru"""
    if not SMS_ENABLED:
        print(f"📱 [SMS бы отправлено]: {message}")
        return
    try:
        url = "https://sms.ru/sms/send"
        params = {"api_id": SMS_API_KEY, "to": YOUR_PHONE, "msg": message, "json": 1}
        response = requests.get(url, params=params)
        print(f"📱 SMS отправлено: {message[:50]}...")
    except Exception as e:
        print(f"❌ Ошибка SMS: {e}")

# ============================================
# ФУНКЦИЯ ОТКРЫТИЯ ВОРОТ
# ============================================
def open_gate():
    """Открывает ворота через Arduino"""
    if arduino:
        arduino.write(b'OPEN\n')
        print("🔌 КОМАНДА OPEN отправлена на Arduino")
        send_sms("🔓 Ворота открыты")
    else:
        print("⚠️ Arduino не подключён, ворота не открылись")

# ============================================
# ФУНКЦИЯ НОРМАЛИЗАЦИИ НОМЕРА (из твоего рабочего кода)
# ============================================
def normalize_plate(text):
    """Гибкая нормализация номера"""
    # 1. Замена латиницы на кириллицу
    lat_to_cyr = {
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
        'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
        'X': 'Х', 'Y': 'У'
    }
    for lat, cyr in lat_to_cyr.items():
        text = text.replace(lat, cyr)

    # 2. Оставляем только буквы и цифры
    text = re.sub(r'[^А-Я0-9]', '', text.upper())

    # 3. Ищем первую букву
    for i, ch in enumerate(text):
        if ch.isalpha():
            text = text[i:]
            break

    # 4. Берём первые 6 символов
    if len(text) > 6:
        text = text[:6]

    # 5. Приводим к формату: буква + 3 цифры + 2 буквы
    if len(text) >= 6:
        result = []

        # Позиция 0: буква
        if text[0].isdigit():
            digit_to_letter = {'0': 'О', '1': 'Р', '2': 'З', '3': 'Е', '4': 'Ч',
                               '5': 'С', '6': 'Б', '7': 'Т', '8': 'В', '9': 'У'}
            result.append(digit_to_letter.get(text[0], 'А'))
        else:
            result.append(text[0])

        # Позиции 1-3: цифры (3 штуки)
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

        # Если цифр меньше 3, добавляем нули
        while digits_count < 3:
            result.append('0')
            digits_count += 1

        # Позиции 4-5: буквы (2 штуки)
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

        # Если букв меньше 2, добавляем 'А'
        while letters_count < 2:
            result.append('А')
            letters_count += 1

        text = ''.join(result[:6])

    return text

# ============================================
# ФУНКЦИЯ ДОБАВЛЕНИЯ ВРЕМЕННОЙ МЕТКИ
# ============================================
def add_timestamp(frame):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, current_time, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

# ============================================
# ОСНОВНОЙ ЦИКЛ С КАМЕРОЙ
# ============================================
def main():
    global recording, video_writer, recording_start_time
    global last_car_detected_time, car_detected, sms_sent_for_current_car

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Не удалось открыть камеру")
        print("Попробуй подключить внешнюю камеру или используй телефон")
        return

    print("\n" + "="*50)
    print("✅ КАМЕРА ЗАПУЩЕНА")
    print("="*50)
    print("📹 Запись начнётся автоматически при обнаружении автомобиля")
    print("🔍 Распознавание номеров включено")
    print("📱 SMS-уведомления", "ВКЛЮЧЕНЫ" if SMS_ENABLED else "ВЫКЛЮЧЕНЫ (демо-режим)")
    print("🔌 Управление воротами:", "ВКЛЮЧЕНО" if arduino else "ВЫКЛЮЧЕНО")
    print("\nНажми 'q' для выхода")
    print("="*50 + "\n")

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Не удалось захватить кадр")
            break

        frame = add_timestamp(frame)
        frame_count += 1

        # Обрабатываем каждый 3-й кадр для производительности
        if frame_count % 3 == 0:
            results = model(frame, conf=0.3)
            cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]

            if cars:
                # ===== ОБНАРУЖЕНА МАШИНА =====
                if not car_detected:
                    car_detected = True
                    print(f"\n🚗 АВТОМОБИЛЬ ОБНАРУЖЕН в {datetime.datetime.now().strftime('%H:%M:%S')}")
                    sms_sent_for_current_car = False

                    # НАЧАЛО ЗАПИСИ ВИДЕО
                    if not recording:
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(VIDEO_SAVE_PATH, f"car_{timestamp}.avi")
                        h, w = frame.shape[:2]
                        fourcc = cv2.VideoWriter_fourcc(*'XVID')
                        video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
                        if video_writer.isOpened():
                            recording = True
                            recording_start_time = time.time()
                            print(f"🎥 НАЧАЛО ЗАПИСИ: {filename}")

                last_car_detected_time = time.time()

                # ===== РАСПОЗНАВАНИЕ НОМЕРА =====
                for car in cars:
                    x1, y1, x2, y2 = map(int, car.xyxy[0].tolist())
                    car_h = y2 - y1
                    car_w = x2 - x1

                    # Вырезаем номер
                    y1_plate = y1 + int(car_h * 0.50)
                    y2_plate = y1 + int(car_h * 0.92)
                    x1_plate = x1 + int(car_w * 0.15)
                    x2_plate = x2 - int(car_w * 0.15)

                    plate = frame[y1_plate:y2_plate, x1_plate:x2_plate]

                    if plate.size > 0:
                        # Увеличиваем для OCR
                        h_plate, w_plate = plate.shape[:2]
                        if h_plate < 80:
                            scale = 120 / h_plate
                            plate = cv2.resize(plate, (int(w_plate * scale), 120),
                                              interpolation=cv2.INTER_CUBIC)

                        # Распознавание
                        try:
                            result = reader.readtext(plate)
                            if result:
                                raw_text = result[0][1].upper()
                                confidence = result[0][2]
                                normalized = normalize_plate(raw_text)

                                print(f"🔍 Распознано: {raw_text} → {normalized} (уверенность: {confidence:.3f})")

                                if normalized in ALLOWED_PLATES:
                                    print(f"🔓 ДОСТУП РАЗРЕШЁН! Номер {normalized} в базе")
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                    cv2.putText(frame, f"GRANTED: {normalized}", (x1, y1-10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                    open_gate()
                                else:
                                    print(f"🔒 ДОСТУП ЗАПРЕЩЁН! Номер {normalized} не в базе")
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                    cv2.putText(frame, f"DENIED: {normalized}", (x1, y1-10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                                    if not sms_sent_for_current_car:
                                        send_sms(f"❌ Доступ запрещён. Номер {normalized} не в базе")
                                        sms_sent_for_current_car = True
                            else:
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                                cv2.putText(frame, "Plate not recognized", (x1, y1-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                                if not sms_sent_for_current_car:
                                    send_sms("⚠️ Автомобиль обнаружен, но номер не распознан")
                                    sms_sent_for_current_car = True
                        except Exception as e:
                            print(f"⚠️ Ошибка OCR: {e}")

            else:
                # ===== МАШИНЫ НЕТ =====
                if car_detected:
                    if time.time() - last_car_detected_time > NO_CAR_TIMEOUT:
                        car_detected = False
                        print(f"\n🚫 АВТОМОБИЛЬ ПОКИНУЛ ЗОНУ в {datetime.datetime.now().strftime('%H:%M:%S')}")

                        # ОСТАНОВКА ЗАПИСИ
                        if recording and video_writer:
                            video_writer.release()
                            video_writer = None
                            duration = time.time() - recording_start_time
                            print(f"🛑 ЗАПИСЬ ОСТАНОВЛЕНА (длительность: {duration:.1f} сек)")
                            recording = False

        # Запись кадра в видео
        if recording and video_writer:
            video_writer.write(frame)

        # Показываем видео
        cv2.imshow("Gate Control", frame)

        # Выход по 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Завершение
    cap.release()
    if video_writer:
        video_writer.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()
    print("\n✅ Программа завершена")

if __name__ == "__main__":
    main()
