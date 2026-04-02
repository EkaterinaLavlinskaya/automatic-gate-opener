
# 🚗 Automatic Gate Control System

Система автоматического распознавания автомобильных номеров для контроля доступа.  
Камера → YOLO → OCR → Проверка базы → Arduino → Ворота.

## 🎥 Демо

![Demo](automatic-gate/recordings/demo.gif)
*Короткое видео работы системы можно посмотреть [по ссылке]([docs/car_20260402_114401.avi](https://drive.google.com/file/d/11ftFWCySe6rMIT_O_HFaOPrpFJD6Pzfn/view?usp=sharing))*

## 📋 Возможности

- 🎯 **Детекция автомобиля** — YOLOv11 (или дообученная модель)
- 🔍 **Распознавание номера** — EasyOCR / PaddleOCR
- 📱 **SMS-уведомления** — через SMS.ru
- 🎥 **Автозапись видео** — при появлении автомобиля
- ⏱️ **Временная метка** — на каждом кадре
- 🔌 **Управление воротами** — Arduino + реле

## 🏗️ Архитектура
Камера → YOLO (детекция машины) → Вырезание номера → OCR → Проверка базы → Arduino → Ворота
↓
SMS при неизвестном номере



## 🛠️ Установка

### 1. Клонируй репозиторий
```bash
git clone https://github.com/ваш-username/automatic-gate.git
cd automatic-gate
2. Создай виртуальное окружение
bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
3. Установи зависимости
bash
pip install -r requirements.txt
4. Настрой базу номеров
Отредактируй data/allowed_plates.csv:

csv
plate
А273КК
Н642ВУ
5. Настрой SMS (опционально)
В gate_system.py укажи API ключ и номер телефона:

python
SMS_API_KEY = "ваш_ключ"
YOUR_PHONE = "+7XXXXXXXXXX"
6. Подключи Arduino
Загрузи скетч arduino/gate_control.ino в Arduino и укажи COM-порт в коде:

python
arduino = serial.Serial('COM3', 9600, timeout=1)
7. Запусти систему
bash
python gate_system.py
📊 Результаты тестирования
Показатель	Результат
Тестовых фото	16
Детекция автомобиля	93%
Распознавание номера	75%
Точность доступа	100%
🧪 Тестирование на фото
bash
python plate_reader.py --image test.jpg
📁 Структура проекта

automatic-gate/
├── gate_system.py          # Основной скрипт с камерой
├── plate_reader.py         # Тестирование на фото
├── requirements.txt        # Зависимости
├── data/
│   └── allowed_plates.csv  # База номеров
├── recordings/             # Видео с записями
├── arduino/
│   └── gate_control.ino    # Скетч для Arduino
└── docs/
    └── schema.png          # Схема работы
📦 Зависимости
Python 3.8+

ultralytics

easyocr (или paddleocr)

opencv-python

pyserial

requests

🔧 Настройка под себя
Модель YOLO: замени yolo11n.pt на свою best.pt

OCR: можно заменить EasyOCR на PaddleOCR,в зависимости от качества вашей камеры могут понадобиться дополнительные настройки easyocr

SMS: можно заменить на другой провайдер (Beeline, MTS Exolve)

📝 Логирование
Все события сохраняются в консоль с временными метками:


🕒 14:30:22 | А27ЗКК → А273КК (conf: 0.44)
🔓 ДОСТУП РАЗРЕШЁН! А273КК в базе
🎥 Начата запись: recordings/car_20260331_143022.avi
🚀 Планы по улучшению
Веб-интерфейс для просмотра истории

Telegram-бот вместо SMS

Cloud-синхронизация базы номеров

Улучшение распознавания в ночное время

📄 Лицензия
MIT

👤 Автор
Екатерина Лавлинская
GitHub

Проект создан в рамках курса по Computer Vision и Embedded Systems
