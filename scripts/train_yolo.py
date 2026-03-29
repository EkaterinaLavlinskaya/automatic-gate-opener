# -*- coding: utf-8 -*-
"""Дообучение YOLOv3 на собственном датасете (фронтальные машины)

   Проект: Smart Gate
"""

import os

# ==================== 1. ЗАГРУЗКА ДАННЫХ ====================
# Ссылка на архив с фото и разметкой (замени на свою)
# Формат: папка с фото (45 шт) и txt-файлами разметки (YOLO format)
ARCHIVE_ID = "1h2j5hZnGbT8YZjc6elJwZ3Lizeo6J-iJ"  # ← вставь свой ID

!wget "https://drive.usercontent.google.com/download?id={ARCHIVE_ID}&export=download&confirm=t" -O dataset.rar

# Распаковка
!apt-get install -y unrar
!unrar x dataset.rar

# ==================== 2. НАСТРОЙКА DARKNET ====================
if not os.path.exists('darknet'):
    !git clone https://github.com/pjreddie/darknet.git

%cd darknet

# Компиляция
!make

# ==================== 3. ПОДГОТОВКА ДАННЫХ ====================
# Очищаем старые данные
!rm -rf data/custom
!mkdir -p data/custom

# Копируем файлы (папка распакованного архива называется "Ав")
!cp ../Ав/*.jpg data/custom/
!cp ../Ав/*.txt data/custom/

print("Проверка данных:")
!echo "Фото:" && ls data/custom/*.jpg | wc -l
!echo "Разметка:" && ls data/custom/*.txt | wc -l

# Создаем train.txt (список всех фото)
!find data/custom -name "*.jpg" > train.txt

# Создаем classes.names (один класс — car)
!echo "car" > data/custom/classes.names

# Создаем custom.data
with open('data/custom.data', 'w') as f:
    f.write("classes = 1\n")
    f.write("train = /content/darknet/train.txt\n")
    f.write("valid = /content/darknet/train.txt\n")
    f.write("names = data/custom/classes.names\n")
    f.write("backup = /content/darknet/backup\n")

# ==================== 4. НАСТРОЙКА КОНФИГА YOLO ====================
# Копируем оригинальный конфиг
!cp cfg/yolov3.cfg cfg/yolov3_custom.cfg

# Редактируем под наш датасет
!sed -i 's/batch=64/batch=16/' cfg/yolov3_custom.cfg
!sed -i 's/subdivisions=16/subdivisions=8/' cfg/yolov3_custom.cfg
!sed -i 's/width=608/width=416/' cfg/yolov3_custom.cfg
!sed -i 's/height=608/height=416/' cfg/yolov3_custom.cfg
!sed -i 's/classes=80/classes=1/' cfg/yolov3_custom.cfg
!sed -i 's/filters=255/filters=18/' cfg/yolov3_custom.cfg

# ==================== 5. ЗАГРУЗКА ПРЕДОБУЧЕННЫХ ВЕСОВ ====================
if not os.path.exists("darknet53.conv.74"):
    print("Скачиваем предобученные веса...")
    !wget https://pjreddie.com/media/files/darknet53.conv.74

# ==================== 6. ЗАПУСК ОБУЧЕНИЯ ====================
print("\n✅ Начинаем обучение...")
print("Размер: 416x416, сохранение в backup/ каждые 100 итераций")
print("Ожидаемое время: 30-60 минут\n")

!./darknet detector train data/custom.data cfg/yolov3_custom.cfg darknet53.conv.74 -dont_show -map

# ==================== 7. СОХРАНЕНИЕ РЕЗУЛЬТАТА ====================
print("\n✅ Обучение завершено. Скачиваем веса...")
from google.colab import files

# Проверяем, есть ли файл
weights_path = '/content/darknet/backup/yolov3_custom_last.weights'
if os.path.exists(weights_path):
    files.download(weights_path)
    print("✅ Файл yolov3_custom_last.weights скачан")
else:
    print("❌ Веса не найдены. Проверьте backup/")
    !ls -la /content/darknet/backup/

Как использовать этот скрипт
Подготовь архив dataset.rar со структурой:

text
Ав/
├── image1.jpg
├── image1.txt
├── image2.jpg
├── image2.txt
...
Получи ID файла из ссылки Google Drive:

text
https://drive.google.com/file/d/1h2j5hZnGbT8YZjc6elJwZ3Lizeo6J-iJ/view
ID = 1h2j5hZnGbT8YZjc6elJwZ3Lizeo6J-iJ
Вставь ID в переменную ARCHIVE_ID

Запусти в Colab → через 30–60 минут получишь yolov3_custom_last.weights

