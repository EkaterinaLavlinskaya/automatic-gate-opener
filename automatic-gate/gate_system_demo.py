import cv2
import serial
import time
import datetime
import os
import sys
from ultralytics import YOLO

# ============================================
# НАСТРОЙКИ
# ============================================
# Arduino (проверь COM-порт!)
try:
    arduino = serial.Serial('COM4', 9600, timeout=1)
    time.sleep(2)
    print("✅ Arduino подключён")
except:
    arduino = None
    print("⚠️ Arduino не найден, работаем без него")

# Папка для видео
VIDEO_SAVE_PATH = "recordings"
if not os.path.exists(VIDEO_SAVE_PATH):
    os.makedirs(VIDEO_SAVE_PATH)

# Загрузка модели YOLO
print("Загрузка YOLO...")
model = YOLO("yolo11n.pt")
print("✅ YOLO загружен")

# Переменные для записи видео
recording = False
video_writer = None
recording_start_time = 0

# Переменные для завершения
gate_opened = False
program_completed = False


# ============================================
# ФУНКЦИИ
# ============================================
def add_timestamp(frame):
    """Добавляет временную метку на кадр"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, current_time, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame


def open_gate():
    """Открывает ворота через Arduino"""
    global gate_opened
    if arduino:
        arduino.write(b'OPEN\n')
        print("🔌 КОМАНДА OPEN отправлена на Arduino")
        gate_opened = True
    else:
        print("⚠️ Arduino не подключён, ворота не открылись")
        gate_opened = True  # Для демо считаем, что открылись


def complete_program():
    """Завершает программу"""
    global program_completed
    program_completed = True
    print("\n✅ Блокировка снята, обнаружение машин возобновлено")
    print("✅ Демо-программа завершена")

    # Небольшая задержка перед выходом
    time.sleep(1)

    # Завершаем
    if recording and video_writer:
        video_writer.release()
    if arduino:
        arduino.close()
    cv2.destroyAllWindows()
    sys.exit(0)


# ============================================
# ОСНОВНОЙ ЦИКЛ С КАМЕРОЙ
# ============================================
def main():
    global recording, video_writer, recording_start_time, gate_opened, program_completed

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Не удалось открыть камеру")
        return

    print("\n" + "=" * 50)
    print("✅ ДЕМО-РЕЖИМ: РАСПОЗНАВАНИЕ АВТОМОБИЛЕЙ")
    print("=" * 50)
    print("📹 Запись начнётся при обнаружении автомобиля")
    print("🔓 При обнаружении автомобиля ворота открываются")
    print("🚫 Программа завершится после открытия ворот")
    print("\nНажми 'q' для выхода")
    print("=" * 50 + "\n")

    frame_count = 0
    car_detected = False
    access_granted = False

    while not program_completed:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Не удалось захватить кадр")
            break

        frame = add_timestamp(frame)
        frame_count += 1

        # Обрабатываем каждый 3-й кадр
        if frame_count % 3 == 0 and not access_granted:
            results = model(frame, conf=0.3)
            cars = [box for box in results[0].boxes if int(box.cls[0]) == 2]

            if cars and not car_detected:
                # ===== ОБНАРУЖЕНА МАШИНА =====
                car_detected = True
                access_granted = True

                print(f"\n🚗 АВТОМОБИЛЬ ОБНАРУЖЕН в {datetime.datetime.now().strftime('%H:%M:%S')}")
                print("🔓 ДОСТУП РАЗРЕШЁН! ВОРОТА ОТКРЫВАЮТСЯ")
                open_gate()

                # НАЧАЛО ЗАПИСИ ВИДЕО
                if not recording:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(VIDEO_SAVE_PATH, f"car_{timestamp}.avi")
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
                    if video_writer.isOpened():
                        recording = True
                        recording_start_time = time.time()
                        print(f"🎥 НАЧАЛО ЗАПИСИ: {filename}")

                # ===== ОТРИСОВКА КВАДРАТА И ПОДПИСИ =====
                for car in cars:
                    x1, y1, x2, y2 = map(int, car.xyxy[0].tolist())
                    confidence = float(car.conf[0])

                    # Зелёный квадрат вокруг машины
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    label = f"car: {confidence:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, "ACCESS GRANTED", (50, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

                # Записываем несколько кадров после обнаружения
                for i in range(30):  # ~1 секунда видео
                    if recording and video_writer:
                        video_writer.write(frame)
                    cv2.imshow("Gate Control - DEMO", frame)
                    cv2.waitKey(33)

                # Останавливаем запись
                if recording and video_writer:
                    video_writer.release()
                    video_writer = None
                    duration = time.time() - recording_start_time
                    print(f"🛑 ЗАПИСЬ ОСТАНОВЛЕНА (длительность: {duration:.1f} сек)")
                    recording = False

                # Завершаем программу
                complete_program()

            elif cars:
                # Рисуем квадрат для отображения
                for car in cars:
                    x1, y1, x2, y2 = map(int, car.xyxy[0].tolist())
                    confidence = float(car.conf[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"car: {confidence:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Запись кадра в видео (если идёт запись)
        if recording and video_writer:
            video_writer.write(frame)

        # Показываем видео
        cv2.imshow("Gate Control - DEMO", frame)

        # Выход по 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Завершение
    cap.release()
    if video_writer:
        video_writer.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()


if __name__ == "__main__":
    main()
