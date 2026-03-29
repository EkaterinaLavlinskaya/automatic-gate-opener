import cv2
import easyocr
import pandas as pd
import os
import sys
from ultralytics import YOLO

# Устанавливаем правильную рабочую папку
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"Рабочая папка: {os.getcwd()}")


class PlateReader:
    def __init__(self):
        self.model = YOLO("best.pt")  # моя дообученная модель
        self.reader = easyocr.Reader(["ru", "en"], gpu=False)

        # Создаём папку data и файл с базой, если их нет
        os.makedirs("data", exist_ok=True)
        db_path = "data/allowed_plates.csv"
        if not os.path.exists(db_path):
            with open(db_path, "w", encoding="utf-8") as f:
                f.write("plate\n136\nA123BC\nB456CD\nX999XX\nK777AA\nН642ВУ\nАА273КК\n")
            print(f"✅ Создан файл: {db_path}")

        self.allowed_df = pd.read_csv(db_path, encoding='cp1251')
        self.allowed_plates = set(
            self.allowed_df["plate"].astype(str).str.upper().values
        )
        print(f"✅ Загружено разрешённых номеров: {len(self.allowed_plates)}")

    def detect_plate(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None, "Не удалось загрузить изображение"

        height, width = img.shape[:2]
        if width > 1280:
            scale = 1280 / width
            new_width = 1280
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))

        results = self.model(img, conf=0.3)  # порог уверенности 30%)

        # Модель обучена на одном классе (0 — это машина)
        cars = [box for box in results[0].boxes if int(box.cls[0]) == 0]
        if len(cars) == 0:
            return None, "Машина не найдена"

        box = cars[0]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

        plate_y1 = y1 + int((y2 - y1) * 0.6)
        plate_y2 = y2
        plate_x1 = x1 + int((x2 - x1) * 0.15)
        plate_x2 = x2 - int((x2 - x1) * 0.15)

        plate_y1 = max(0, plate_y1)
        plate_y2 = min(img.shape[0], plate_y2)
        plate_x1 = max(0, plate_x1)
        plate_x2 = min(img.shape[1], plate_x2)

        if plate_y2 <= plate_y1 or plate_x2 <= plate_x1:
            return None, "Область номера слишком мала"

        plate_crop = img[plate_y1:plate_y2, plate_x1:plate_x2]
        plate_crop = cv2.convertScaleAbs(plate_crop, alpha=1.5, beta=0)

        try:
            ocr_result = self.reader.readtext(plate_crop)
            if len(ocr_result) == 0:
                return plate_crop, "Текст не распознан"
            plate_text = ocr_result[0][1].upper().replace(" ", "").replace("-", "")
            return plate_crop, plate_text
        except Exception as e:
            return plate_crop, f"Ошибка OCR"

    def process(self, image_path):
        crop, text = self.detect_plate(image_path)
        is_allowed = (
            text in self.allowed_plates
            if text
            not in [
                "Машина не найдена",
                "Текст не распознан",
                "Не удалось загрузить изображение",
            ]
            else False
        )

        # СОХРАНЯЕМ ВЫРЕЗАННЫЙ НОМЕР
        if crop is not None:
            save_path = os.path.join(os.getcwd(), "cropped_plate.jpg")
            cv2.imwrite(save_path, crop)
            print(f"✅ Вырезанный номер сохранён: {save_path}")

        return {
            "plate_text": text,
            "is_allowed": is_allowed,
            "message": "✅ ДОСТУП РАЗРЕШЁН" if is_allowed else "❌ ДОСТУП ЗАПРЕЩЁН",
            "success": text not in ["Машина не найдена", "Текст не распознан"],
            "cropped_image": crop,
        }


if __name__ == "__main__":
    reader = PlateReader()

    # Укажи путь к своему фото (исправь при необходимости)
    image_path = (
        r"C:\MyPythonProjects\AV\yolo-coco\images\Сканирование_20260328-1918-11.jpg"
    )

    if not os.path.exists(image_path):
        print(f"❌ Файл не найден: {image_path}")
        sys.exit(1)

    result = reader.process(image_path)

    print(f"\n📝 Распознанный номер: {result['plate_text']}")
    print(f"🔐 Результат: {result['message']}")
    print(f"📋 В базе: {result['is_allowed']}")
