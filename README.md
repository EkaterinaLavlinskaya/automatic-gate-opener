smart-gate/
├── README.md                 # Главное описание проекта
├── requirements.txt          # Все зависимости (opencv-python, pyserial и т.д.)
├── .gitignore               # Что не загружать (__pycache__, видеофайлы)
│
├── gate_control/            # Модуль управления воротами
│   ├── __init__.py
│   └── controller.py        # Скрипт с классом для открытия/закрытия
│
├── camera/                  # Модуль камеры
│   ├── __init__.py
│   └── recorder.py          # Скрипт для записи видео
│
├── scripts/                 # Готовые скрипты для запуска
│   ├── open_gate.py         # Открыть ворота
│   ├── close_gate.py        # Закрыть ворота
│   └── record_video.py      # Записать видео
│
├── tests/                   # Тесты (опционально)
│   └── test_controller.py
│
├── recordings/              # Папка для видео (игнорируется git)
│   └── .gitkeep            # Чтобы папка была в репозитории
│
└── docs/                    # Документация
    ├── hardware.md          # Схема подключения реле, pinout
    └── setup.md             # Инструкция по установке

#  Автоматическая система распознавания номеров для контроля доступа
Цель за 3 недели Создать работающий прототип, который:  принимает изображение автомобиля,  распознает номер,  проверяет по базе разрешенных номеров,  возвращает решение (доступ открыт/закрыт),  и всё это в виде структурированного репозитория с README и демо.
# 🚗 Automatic Gate Control with License Plate Recognition

[![Tests](https://github.com/EkaterinaLavlinskaya/automatic-gate/actions/workflows/test.yml/badge.svg)](https://github.com/.../actions)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://hub.docker.com/...)

## 📌 Business Context
Система для автоматического контроля доступа на парковку / КПП. Распознает номер автомобиля по изображению и проверяет его в базе разрешенных.

## 🎯 Key Features
- **Detection**: YOLOv8 для локализации номера
- **OCR**: EasyOCR (поддержка русского и английского)
- **Access control**: проверка по базе (CSV/SQLite)
- **API**: REST API на FastAPI
- **Docker**: контейнеризация для легкого развертывания
- **Tests**: юнит- и интеграционные тесты

## 🖼️ Demo
[Видео-демо (1 мин)]()  
[Скриншоты API]()  
[Примеры работы]()  

## 🏗️ Project Structure
(краткое описание папок)

## 🚀 Quick Start
### Option 1: Docker (recommended)
```bash
docker-compose up --build
# API доступно на http://localhost:8000
# Swagger: http://localhost:8000/docs
