import cv2
import easyocr
from ultralytics import YOLO

class PlateReader:
    def __init__(self):
        # Готовая модель YOLO для номеров (не требует дообучения)
        self.model = YOLO("keremberke/yolov8m-license-plate")
        # EasyOCR с поддержкой русского и английского
        self.reader = easyocr.Reader(['ru', 'en'])
    
    def detect_plate(self, image_path):
        """Находит номер на изображении, возвращает обрезанную картинку и текст"""
        results = self.model(image_path)
        
        # Проверяем, есть ли детекции
        if len(results[0].boxes) == 0:
            return None, "Номер не найден"
        
        # Берём первую детекцию (самую уверенную)
        box = results[0].boxes[0]
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        
        # Загружаем и обрезаем изображение
        img = cv2.imread(image_path)
        plate_crop = img[y1:y2, x1:x2]
        
        # Распознаём текст
        ocr_result = self.reader.readtext(plate_crop)
        if len(ocr_result) == 0:
            return plate_crop, "Текст не распознан"
        
        plate_text = ocr_result[0][1].upper().replace(" ", "")
        return plate_crop, plate_text
    
    def process(self, image_path):
        """Основной метод: возвращает результат"""
        crop, text = self.detect_plate(image_path)
        return {
            "plate_text": text,
            "success": text not in ["Номер не найден", "Текст не распознан"],
            "cropped_image": crop
        }


# Тестирование
if __name__ == "__main__":
    reader = PlateReader()
    
    # Укажи путь к любому фото с машиной (где виден номер)
    result = reader.process("data/test_images/car_with_plate.jpg")
    
    print(f"Распознанный номер: {result['plate_text']}")
    print(f"Успех: {result['success']}")
    
    if result['cropped_image'] is not None:
        cv2.imshow("Cropped Plate", result['cropped_image'])
        cv2.waitKey(0)
        cv2.destroyAllWindows()
