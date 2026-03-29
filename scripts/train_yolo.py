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



---

## 📊 1. На сколько эпох обучается модель?

**Нигде не указано явно.** В конфиге YOLOv3 нет параметра "epochs". Обучение идет **бесконечно**, пока ты не остановишь.

В строке запуска:
```bash
!./darknet detector train data/custom.data cfg/yolov3_custom.cfg darknet53.conv.74 -dont_show -map
```

Параметр `-map` заставляет считать mAP каждые 100 итераций, но **не ограничивает количество итераций**.

Остановка — вручную, когда loss перестал снижаться (обычно 2000–5000 итераций для YOLOv3).

---

## ⚙️ 2. Какие оптимизаторы используются?

**В YOLOv3 используется SGD (Stochastic Gradient Descent) с моментом.**

Это задается в конфиге `yolov3_custom.cfg`:

```
[net]
momentum=0.9
decay=0.0005
learning_rate=0.001
policy=steps
steps=400000,450000
scales=.1,.1
```

| Параметр | Значение | Что значит |
|----------|----------|------------|
| **optimizer** | SGD (hardcoded) | Стохастический градиентный спуск |
| **momentum** | 0.9 | Сглаживает обновления весов |
| **decay** | 0.0005 | L2-регуляризация (weight decay) |
| **learning_rate** | 0.001 | Начальная скорость обучения |
| **policy** | steps | Уменьшаем lr на определенных шагах |
| **steps** | 400000, 450000 | На этих итерациях уменьшаем lr в 10 раз |

**Важно:** эти настройки рассчитаны на обучение с нуля на 500k итераций. Для дообучения они тоже работают.

---

## 🧠 3. Какие функции активации используются?

В YOLOv3 везде используется **Leaky ReLU** (кроме последнего слоя).

В конфиге это указано как `activation=leaky`:

```
[convolutional]
batch_normalize=1
filters=32
size=3
stride=1
pad=1
activation=leaky   # ← здесь
```

**Исключение:** последний слой каждого масштаба (`yolo` layer) использует **линейную активацию** (без нелинейности), так как это детекционный слой.

---

## 🏗️ 4. Сколько слоев?

YOLOv3 имеет **106 слоев** (включая conv, route, upsample, yolo).

Твой конфиг `yolov3_custom.cfg` показывает их все при запуске. В логе ты видишь:

```
layer     filters    size              input                output
    0 conv     32  3 x 3 / 1   416 x 416 x   3   ->   416 x 416 x  32
    1 conv     64  3 x 3 / 2   416 x 416 x  32   ->   208 x 208 x  64
    ...
  106 yolo
```

**Итог:** 106 слоев, из них:
- 75 convolutional (с batch norm + leaky)
- 6 yolo (детекционные, на 3 масштабах)
- 3 route (соединения)
- 3 upsample
- Остальные — shortcut (residual connections)

---

## 📝 Где все это указано?

| Что | Где указано |
|-----|-------------|
| **Архитектура** | `cfg/yolov3_custom.cfg` |
| **Количество слоев** | В логе запуска (счетчик от 0 до 106) |
| **Оптимизатор** | Hardcoded в исходниках darknet (SGD) |
| **Learning rate, momentum, decay** | В `[net]` секции конфига |
| **Активации** | В каждом `[convolutional]` блоке |
| **Количество итераций** | Не ограничено, остановка вручную |

---

## 🎯 Как управлять количеством итераций?

Если хотите ограничить обучение, добавьте в конфиг параметр `max_batches`:

```
[net]
max_batches = 2000
```

Тогда обучение остановится после 2000 итераций. Но для дообучения обычно хватает 1000–2000.

---

## 💡 Этот скрипт использует:

- **Архитектуру:** YOLOv3 (106 слоев)
- **Оптимизатор:** SGD с momentum 0.9
- **Активации:** Leaky ReLU (кроме выхода)
- **Количество итераций:** не ограничено (ты остановишь вручную)
- **Размер батча:** 16 (уменьшен с 64)
- **Размер изображения:** 416×416

Все настройки наследуются из оригинального `yolov3.cfg`.


