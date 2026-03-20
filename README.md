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
