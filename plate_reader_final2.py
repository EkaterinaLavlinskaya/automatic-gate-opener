import cv2
import pytesseract
import pandas as pd
import os
import sys
import re
from ultralytics import YOLO

# Укажи свой путь к tesseract (ПРОВЕРЬ ЭТОТ ПУТЬ!)
tesseract_path = r"C:\MyPythonProjects\AV\tesseract-ocr-w64-setup-5.5.0.20241111.exe"
if not os.path.exists(tesseract_path):
    print(f"❌ Tesseract не найден по пути: {tesseract_path}")
    print("Укажи правильный путь в переменной tesseract_path")
    sys.exit(1)
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Устанавливаем правильную рабочую папку
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"Рабочая папка: {os.getcwd()}")


class PlateReader:
    def __init__(self):
        self.model = YOLO("best.pt")
        print("✅ Модель YOLO загружена")

        # Создаём папку и файл с базой номеров
        os.makedirs("data", exist_ok=True)
        db_path = os.path.join("data", "allowed_plates.csv")
        
        if not os.path.exists(db_path):
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("plate\n136\nA123BC\nB456CD\nX999XX\nK777AA\nА273КК\nН642ВУ\n")
            print(f"✅ Создан файл: {db_path}")

        self.allowed_df = pd.read_csv(db_path, encoding='utf-8')
        self.allowed_plates = set(
            self.allowed_df["plate"].astype(str).str.upper().values
        )
        print(f"✅ Загружено разрешённых номеров: {len(self.allowed_plates)}")

    def preprocess_for_ocr(self, img_bgr):
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        white_pixels = cv2.countNonZero(binary)
        total_pixels = binary.shape[0] * binary.shape[1]
        if white_pixels > total_pixels / 2:
            binary = cv2.bitwise_not(binary)
        return binary

    def normalize_plate_text(self, text):
        if not text:
            return ""
        lat_to_cyr = {
            'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
            'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
            'X': 'Х', 'Y': 'У', 'I': '1'
        }
        result = []
        for ch in text.upper():
            result.append(lat_to_cyr.get(ch, ch))
        text = ''.join(result)
        text = re.sub(r'[^А-Я0-9]', '', text)
        if len(text) >= 6:
            text = text[:6]
            if text[0].isdigit():
                digit_to_letter = {'0': 'О', '1': 'Р', '2': 'З', '3': 'Е', '4': 'Ч',
                                   '5': 'С', '6': 'Б', '7': 'Т', '8': 'В', '9': 'У'}
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
        
        cars = [box for box in results[0].boxes if int(box.cls[0]) == 0]
        if len(cars) == 0:
            return None, "Машина не найдена"

        print("3. Машина найдена, вырезаем номер...")
        box = cars[0]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        
        car_height = y2 - y1
        car_width = x2 - x1
        
        plate_y1 = y1 + int(car_height * 0.65)
        plate_y2 = y1 + int(car_height * 0.88)
        plate_x1 = x1 + int(car_width * 0.25)
        plate_x2 = x2 - int(car_width * 0.25)

        plate_y1 = max(0, plate_y1)
        plate_y2 = min(img.shape[0], plate_y2)
        plate_x1 = max(0, plate_x1)
        plate_x2 = min(img.shape[1], plate_x2)

        plate_crop = img[plate_y1:plate_y2, plate_x1:plate_x2]
        print(f"4. Размер вырезанной области: {plate_crop.shape}")
        
        print("5. Подготовка для Tesseract...")
        h, w = plate_crop.shape[:2]
        if w < 200 or h < 50:
            scale = max(200 / w, 50 / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            plate_crop = cv2.resize(plate_crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        processed = self.preprocess_for_ocr(plate_crop)
        cv2.imwrite("debug_ocr_input.jpg", processed)
        
        print("6. Распознавание текста (Tesseract)...")
        custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=АВЕКМНОРСТУХ1234567890'
        raw_text = pytesseract.image_to_string(processed, lang='rus+eng', config=custom_config)
        raw_text = raw_text.strip().replace(" ", "").replace("-", "").replace("\n", "")
        print(f"7. Raw text: {raw_text}")
        
        cleaned_text = self.normalize_plate_text(raw_text)
        print(f"8. Cleaned text: '{cleaned_text}'")
        
        return plate_crop, cleaned_text

    def process(self, image_path):
        crop, text = self.detect_plate(image_path)
        is_allowed = text in self.allowed_plates if text else False

        if crop is not None:
            cv2.imwrite("cropped_plate.jpg", crop)
            print(f"✅ Вырезанный номер сохранён: cropped_plate.jpg")

        return {
            "plate_text": text,
            "is_allowed": is_allowed,
            "message": "✅ ДОСТУП РАЗРЕШЁН" if is_allowed else "❌ ДОСТУП ЗАПРЕЩЁН",
            "cropped_image": crop,
        }


if __name__ == "__main__":
    reader = PlateReader()
    image_path = r"C:\MyPythonProjects\AV\13555_1526314962.jpg"

    if not os.path.exists(image_path):
        print(f"❌ Файл не найден: {image_path}")
        sys.exit(1)

    result = reader.process(image_path)
    print(f"\n📝 Распознанный номер: {result['plate_text']}")
    print(f"🔐 Результат: {result['message']}")
