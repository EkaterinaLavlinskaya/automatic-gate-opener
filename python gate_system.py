import cv2
import easyocr
import serial
import time
import re
from ultralytics import YOLO

# ============================================
# НАСТРОЙКИ
# ============================================
# Подключение к Arduino (проверь COM-порт!)
try:
    arduino = serial.Serial('COM4', 9600, timeout=1)
    time.sleep(2)  # ждём инициализации Arduino
    print("✅ Arduino подключён")
except:
    arduino = None
    print("⚠️ Arduino не найден, работаем без него")

# База разрешённых номеров
ALLOWED_PLATES = {"А273КК", "Н642ВУ"}

# Загрузка моделей
model = YOLO("yolo11n.pt")  # или "best.pt"
reader = easyocr.Reader(['ru', 'en'], gpu=False)

# ============================================
# ФУНКЦИЯ НОРМАЛИЗАЦИИ НОМЕРА
# ============================================
def normalize_plate(text):
    """Приводит распознанный текст к формату А123БВ"""
    # Замена латиницы на кириллицу
    lat_to_cyr = {
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
        'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
        'X': 'Х', 'Y': 'У'
    }
    for lat, cyr in lat_to_cyr.items():
        text = text.replace(lat, cyr)
    
    # Оставляем только буквы и цифры
    text = re.sub(r'[^А-Я0-9]', '', text.upper())
    
    # Ищем первую букву
    for i, ch in enumerate(text):
        if ch.isalpha():
            text = text[i:]
            break
    
    # Берём первые 6 символов
    if len(text) > 6:
        text = text[:6]
    
    # Приводим к формату
    if len(text) >= 6:
        result = []
        
        # Позиция 0: буква
        if text[0].isdigit():
            digit_to_letter = {'0': 'О', '1': 'Р', '2': 'З', '3': 'Е', '4': 'Ч',
                               '5': 'С', '6': 'Б', '7': 'Т', '8': 'В', '9': 'У'}
            result.append(digit_to_letter.get(text[0], 'А'))
        else:
            result.append(text[0])
        
        # Позиции 1-3: цифры
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
        
        # Позиции 4-5: буквы
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
# ОСНОВНОЙ ЦИКЛ (КАМЕРА)
# ============================================
def main():
    # Открываем камеру (0 = встроенная, 1 = USB)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Не удалось открыть камеру")
        return
    
    print("✅ Камера запущена. Нажми 'q' для выхода")
    
    # Для оптимизации: обрабатываем каждый 5-й кадр
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Ошибка захвата кадра")
            break
        
        frame_count += 1
        
        # Обрабатываем каждый 5-й кадр для производительности
        if frame_count % 5 != 0:
            # Всё равно показываем видео
            cv2.imshow("Gate Control", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
        
        # Детекция автомобилей
        results = model(frame, conf=0.3)
        cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]
        
        for car in cars:
            x1, y1, x2, y2 = map(int, car.xyxy[0].tolist())
            car_h = y2 - y1
            car_w = x2 - x1
            
            # Вырезаем область номера
            y1_plate = y1 + int(car_h * 0.50)
            y2_plate = y1 + int(car_h * 0.92)
            x1_plate = x1 + int(car_w * 0.15)
            x2_plate = x2 - int(car_w * 0.15)
            
            plate = frame[y1_plate:y2_plate, x1_plate:x2_plate]
            
            # Распознавание номера
            if plate.size > 0:
                result = reader.readtext(plate)
                
                if result:
                    raw_text = result[0][1].upper()
                    confidence = result[0][2]
                    normalized = normalize_plate(raw_text)
                    
                    print(f"🔍 Распознано: {raw_text} → {normalized} (уверенность: {confidence:.2f})")
                    
                    # Проверка доступа
                    if normalized in ALLOWED_PLATES:
                        print(f"🔓 ДОСТУП РАЗРЕШЁН! Номер {normalized} в базе")
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"ACCESS GRANTED: {normalized}", (x1, y1-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        # Отправляем команду на Arduino
                        if arduino:
                            arduino.write(b'OPEN\n')
                            print("🔌 Команда OPEN отправлена на Arduino")
                        else:
                            print("⚠️ Arduino не подключён, ворота не открылись")
                    else:
                        print(f"🔒 ДОСТУП ЗАПРЕЩЁН! Номер {normalized} не в базе")
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(frame, f"ACCESS DENIED: {normalized}", (x1, y1-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(frame, "Plate not recognized", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        # Показываем видео
        cv2.imshow("Gate Control", frame)
        
        # Выход по 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    if arduino:
        arduino.close()
        print("✅ Arduino отключён")

if __name__ == "__main__":
    main()
