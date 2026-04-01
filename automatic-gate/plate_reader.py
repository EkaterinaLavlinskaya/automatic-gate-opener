# Создаём базу разрешённых номеров
allowed_plates_list = [
    "А273КК",
    "Н642ВУ",
    "А123ВС",
    "В456CD",
    "X999XX",
    "К777АА"
]

# Сохраняем в CSV
import pandas as pd
db_path = "/content/allowed_plates.csv"
df = pd.DataFrame({"plate": allowed_plates_list})
df.to_csv(db_path, index=False, encoding="utf-8")

print("✅ База номеров создана")
print("Разрешённые номера:")
for plate in allowed_plates_list:
    print(f"   - {plate}")


import cv2
import easyocr
import re
from ultralytics import YOLO
from google.colab import files

# Загружаем модели
model = YOLO("yolo11n.pt")
reader = easyocr.Reader(['ru', 'en'], gpu=False)

# База разрешённых номеров
allowed_plates = ["А273КК", "Н642ВУ", "А123ВС", "В456CD", "X999XX", "К777АА"]

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

# Загрузка фото
print("Загрузи фото для проверки")
uploaded = files.upload()

results_list = []

for filename in uploaded.keys():
    print(f"\n{'='*50}")
    print(f"📸 {filename}")

    img = cv2.imread(filename)
    results = model(img, conf=0.3)
    cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]

    if not cars:
        print("❌ Автомобиль не найден")
        results_list.append({"file": filename, "plate": "", "access": False})
        continue

    box = cars[0]
    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
    car_h = y2 - y1
    car_w = x2 - x1

    # Вырезаем номер
    y1_plate = y1 + int(car_h * 0.50)
    y2_plate = y1 + int(car_h * 0.92)
    x1_plate = x1 + int(car_w * 0.15)
    x2_plate = x2 - int(car_w * 0.15)

    plate = img[y1_plate:y2_plate, x1_plate:x2_plate]

    # Увеличиваем для OCR
    h, w = plate.shape[:2]
    if h < 80:
        scale = 120 / h
        plate = cv2.resize(plate, (int(w * scale), 120), interpolation=cv2.INTER_CUBIC)

    # Распознавание
    result = reader.readtext(plate)

    if result:
        raw_text = result[0][1].upper()
        confidence = result[0][2]
        print(f"🔍 Распознано: '{raw_text}' (уверенность: {confidence:.3f})")

        normalized = normalize_plate(raw_text)
        print(f"📝 Нормализовано: '{normalized}'")

        is_allowed = normalized in allowed_plates
        if is_allowed:
            print("🔓 ДОСТУП РАЗРЕШЁН!")
        else:
            print("🔒 ДОСТУП ЗАПРЕЩЁН!")

        results_list.append({"file": filename, "plate": normalized, "access": is_allowed})
    else:
        print("❌ Номер не распознан")
        results_list.append({"file": filename, "plate": "", "access": False})

# Итог
print("\n" + "="*50)
print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
print("="*50)
for res in results_list:
    status = "✅" if res["access"] else "❌"
    print(f"{status} {res['file']}: {res['plate'] if res['plate'] else '—'}")
