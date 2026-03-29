import cv2
import pytesseract
import pandas as pd
import os
import sys
import re
from ultralytics import YOLO

# Укажи свой путь к tesseract (ИЗМЕНИ ПОД СВОЙ!)
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\MyPythonProjects\AV\tesseract-ocr-w64-setup-5.5.0.20241111.exe"
)

# Устанавливаем правильную рабочую папку
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"Рабочая папка: {os.getcwd()}")


class PlateReader:
    def __init__(self):
        self.model = YOLO("best.pt")
        print("✅ Модель YOLO загружена")

        os.makedirs("data", exist_ok=True)
        db_path = "data/allowed_plates.csv"
        if not os.path.exists(db_path):
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("plate\n136\nA123BC\nB456CD\nX999XX\nK777AA\nН642ВУ\nА273КК\n")
            print(f"✅ Создан файл: {db_path}")

        self.allowed_df = pd.read_csv(db_path, encoding="cp1251")
        self.allowed_plates = set(
            self.allowed_df["plate"].astype(str).str.upper().values
        )
        print(f"✅ Загружено разрешённых номеров: {len(self.allowed_plates)}")

    def preprocess_for_ocr(self, img_bgr):
        """Подготовка изображения для Tesseract"""
        # Конвертируем в серый
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Увеличиваем контраст
        enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

        # Бинаризация
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Инвертируем, если текст светлый на тёмном фоне
        white_pixels = cv2.countNonZero(binary)
        total_pixels = binary.shape[0] * binary.shape[1]
        if white_pixels > total_pixels / 2:
            binary = cv2.bitwise_not(binary)

        return binary

    def normalize_plate_text(self, text):
        """Очистка и нормализация распознанного текста номера"""
        if not text:
            return ""

        # Заменяем латинские буквы на русские
        lat_to_cyr = {
            "A": "А",
            "B": "В",
            "C": "С",
            "E": "Е",
            "H": "Н",
            "K": "К",
            "M": "М",
            "O": "О",
            "P": "Р",
            "T": "Т",
            "X": "Х",
            "Y": "У",
            "I": "1",
        }

        result = []
        for ch in text.upper():
            if ch in lat_to_cyr:
                result.append(lat_to_cyr[ch])
            else:
                result.append(ch)

        text = "".join(result)
        text = re.sub(r"[^А-Я0-9]", "", text)

        # Приводим к формату А123АА (6 символов)
        if len(text) >= 6:
            text = text[:6]
            if text[0].isdigit():
                digit_to_letter = {
                    "0": "О",
                    "1": "Р",
                    "2": "З",
                    "3": "Е",
                    "4": "Ч",
                    "5": "С",
                    "6": "Б",
                    "7": "Т",
                    "8": "В",
                    "9": "У",
                }
                text = digit_to_letter.get(text[0], text[0]) + text[1:]

        return text

    def detect_plate(self, image_path):
        print("1. Загрузка изображения...")
        img = cv2.imread(image_path)
        if img is None:
            return None, "Не удалось загрузить изображение"

        height, width = img.shape[:2]
        if width > 1280:
            scale = 1280 / width
            new_width = 1280
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))

        print("2. Детекция машины...")
        results = self.model(img, conf=0.3)

        print(f"3. Найдено объектов: {len(results[0].boxes)}")
        for box in results[0].boxes:
            print(f"   Класс: {int(box.cls[0])}, уверенность: {float(box.conf[0]):.3f}")

        cars = [box for box in results[0].boxes if int(box.cls[0]) == 0]
        if len(cars) == 0:
            return None, "Машина не найдена"

        print("4. Машина найдена, вырезаем номер...")
        box = cars[0]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

        car_height = y2 - y1
        car_width = x2 - x1

        # Вырезаем область номера (нижняя часть автомобиля)
        plate_y1 = y1 + int(car_height * 0.65)
        plate_y2 = y1 + int(car_height * 0.88)
        plate_x1 = x1 + int(car_width * 0.25)
        plate_x2 = x2 - int(car_width * 0.25)

        plate_y1 = max(0, plate_y1)
        plate_y2 = min(img.shape[0], plate_y2)
        plate_x1 = max(0, plate_x1)
        plate_x2 = min(img.shape[1], plate_x2)

        if plate_y2 <= plate_y1 or plate_x2 <= plate_x1:
            return None, "Область номера слишком мала"

        plate_crop = img[plate_y1:plate_y2, plate_x1:plate_x2]

        print(f"5. Размер вырезанной области: {plate_crop.shape}")

        if plate_crop.size == 0:
            return None, "Область номера пуста"

        print("6. Подготовка для Tesseract...")
        h, w = plate_crop.shape[:2]
        if w < 200 or h < 50:
            scale = max(200 / w, 50 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            plate_crop = cv2.resize(
                plate_crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC
            )
            print(f"   Увеличено до {new_w}x{new_h}")

        # Предобработка
        processed = self.preprocess_for_ocr(plate_crop)

        # Сохраняем для отладки
        cv2.imwrite("debug_ocr_input.jpg", processed)
        print("   Отладка: сохранён debug_ocr_input.jpg")

        print("7. Распознавание текста (Tesseract)...")
        try:
            # Конфиг для распознавания русских номеров
            custom_config = (
                r"--oem 3 --psm 8 -c tessedit_char_whitelist=АВЕКМНОРСТУХ1234567890"
            )
            raw_text = pytesseract.image_to_string(
                processed, lang="rus+eng", config=custom_config
            )
            raw_text = (
                raw_text.strip().replace(" ", "").replace("-", "").replace("\n", "")
            )
            print(f"8. Raw text: {raw_text}")
        except Exception as e:
            print(f"❌ Ошибка Tesseract: {e}")
            return plate_crop, "Ошибка OCR"

        if not raw_text:
            return plate_crop, "Текст не распознан"

        cleaned_text = self.normalize_plate_text(raw_text)
        print(f"9. Cleaned text: '{cleaned_text}'")

        return plate_crop, cleaned_text

    def process(self, image_path):
        crop, text = self.detect_plate(image_path)
        is_allowed = (
            text in self.allowed_plates
            if text
            and text
            not in [
                "Машина не найдена",
                "Текст не распознан",
                "Не удалось загрузить изображение",
                "Ошибка OCR",
            ]
            else False
        )

        if crop is not None:
            save_path = os.path.join(os.getcwd(), "cropped_plate.jpg")
            cv2.imwrite(save_path, crop)
            print(f"✅ Вырезанный номер сохранён: {save_path}")

        return {
            "plate_text": text,
            "is_allowed": is_allowed,
            "message": "✅ ДОСТУП РАЗРЕШЁН" if is_allowed else "❌ ДОСТУП ЗАПРЕЩЁН",
            "success": bool(text)
            and text not in ["Машина не найдена", "Текст не распознан"],
            "cropped_image": crop,
        }


if __name__ == "__main__":
    reader = PlateReader()

    # Тестируем на новом фото
    image_path = r"C:\MyPythonProjects\AV\13555_1526314962.jpg"

    if not os.path.exists(image_path):
        print(f"❌ Файл не найден: {image_path}")
        sys.exit(1)

    result = reader.process(image_path)

    print(f"\n📝 Распознанный номер: {result['plate_text']}")
    print(f"🔐 Результат: {result['message']}")
    print(f"📋 В базе: {result['is_allowed']}")
