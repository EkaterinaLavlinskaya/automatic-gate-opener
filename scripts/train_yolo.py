# ======================================================
# 1. УСТАНОВКА И ПОДГОТОВКА СРЕДЫ
# ======================================================
!apt-get install -y unrar > /dev/null 2>&1
!pip install ultralytics -q

import os
import shutil
from google.colab import files

print("✅ Среда подготовлена")

# ======================================================
# 2. ЗАГРУЗКА ДАТАСЕТА
# ======================================================
print("\n📥 Скачивание датасета yolo-coco.rar...")
!gdown "19lmkRfjapriXecuVaveMVhPsHltLA2EB" -O yolo-coco.rar --quiet

print("📂 Распаковка архива...")
!unrar x yolo-coco.rar /content/dataset_raw/ > /dev/null 2>&1

# ======================================================
# 3. ПРОВЕРКА И КОПИРОВАНИЕ ДАННЫХ
# ======================================================
print("\n🔍 Проверка структуры...")
!ls -la /content/dataset_raw/

# Создаём правильную структуру для YOLO
os.makedirs("/content/dataset/images/train", exist_ok=True)
os.makedirs("/content/dataset/labels/train", exist_ok=True)

# Копируем изображения
if os.path.exists("/content/dataset_raw/images"):
    for f in os.listdir("/content/dataset_raw/images"):
        if f.endswith(('.jpg', '.png', '.jpeg')):
            shutil.copy(
                f"/content/dataset_raw/images/{f}",
                f"/content/dataset/images/train/{f}"
            )

# Копируем разметку
if os.path.exists("/content/dataset_raw/labels"):
    for f in os.listdir("/content/dataset_raw/labels"):
        if f.endswith('.txt'):
            shutil.copy(
                f"/content/dataset_raw/labels/{f}",
                f"/content/dataset/labels/train/{f}"
            )

# Считаем количество
train_images = len(os.listdir("/content/dataset/images/train"))
train_labels = len(os.listdir("/content/dataset/labels/train"))

print(f"\n✅ Скопировано изображений: {train_images}")
print(f"✅ Скопировано файлов разметки: {train_labels}")

if train_images == 0 or train_labels == 0:
    print("\n⚠️ ВНИМАНИЕ: Не найдены изображения или разметка!")
    print("Содержимое папок:")
    !ls -la /content/dataset_raw/
    !ls -la /content/dataset_raw/images/ 2>/dev/null
    !ls -la /content/dataset_raw/labels/ 2>/dev/null

# ======================================================
# 4. СОЗДАНИЕ КОНФИГУРАЦИОННОГО ФАЙЛА
# ======================================================
yaml_content = f"""
path: /content/dataset
train: images/train
val: images/train
nc: 1
names: ['car']
"""

with open("/content/dataset.yaml", "w") as f:
    f.write(yaml_content)

print("\n✅ Файл dataset.yaml создан:")
!cat /content/dataset.yaml

# ======================================================
# 5. ЗАПУСК ОБУЧЕНИЯ
# ======================================================
from ultralytics import YOLO

print("\n🔥 ЗАПУСК ОБУЧЕНИЯ...")
print("=" * 40)

model = YOLO("yolov8n.pt")

results = model.train(
    data="/content/dataset.yaml",
    epochs=100,           # 100 эпох
    imgsz=640,            # размер изображения
    batch=8,              # размер батча
    device=0,             # GPU
    workers=2,
    patience=30,          # ранняя остановка
    save_period=25,       # сохранять каждые 25 эпох
    verbose=True
)

# ======================================================
# 6. ТЕСТИРОВАНИЕ МОДЕЛИ
# ======================================================
print("\n🧪 Тестирование модели на первом изображении...")
test_image = "/content/dataset/images/train/" + os.listdir("/content/dataset/images/train")[0]
results_test = model(test_image)

from google.colab.patches import cv2_imshow
img_with_boxes = results_test[0].plot()
cv2_imshow(img_with_boxes)

# ======================================================
# 7. СКАЧИВАНИЕ МОДЕЛИ
# ======================================================
print("\n📥 Скачивание best.pt на компьютер...")
files.download('/content/runs/detect/train/weights/best.pt')

print("\n" + "=" * 40)
print("✅ ВСЁ ГОТОВО! Модель обучена и скачана.")
print("📁 Путь к модели: /content/runs/detect/train/weights/best.pt")
print("=" * 40)
