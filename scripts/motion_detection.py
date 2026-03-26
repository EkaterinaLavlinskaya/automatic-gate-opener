import cv2
import datetime

# Открываем камеру
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Камера не найдена")
    exit()

# Параметры видео
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = 20.0
fourcc = cv2.VideoWriter_fourcc(*'XVID')

# Переменные для детекции движения
first_frame = None
recording = False
out = None
filename = ""

print("🔍 Ожидание движения...")
print("Нажми 'q' для выхода")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Преобразуем в оттенки серого и размываем для лучшего детектирования
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # Сохраняем первый кадр как фон
    if first_frame is None:
        first_frame = gray
        continue

    # Вычисляем разницу между текущим кадром и фоном
    diff = cv2.absdiff(first_frame, gray)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    # Считаем количество пикселей, которые изменились
    motion_pixels = cv2.countNonZero(thresh)

    # Если движение есть (больше 25000 пикселей)
    if motion_pixels > 25000:
        if not recording:
            # Начинаем запись
            filename = f"C:/Users/Денис/Downloads/motion_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
            out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
            recording = True
            print(f"🎬 ДВИЖЕНИЕ! Запись: {filename}")

        # Добавляем таймстамп на кадр
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "MOTION DETECTED", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Записываем кадр
        out.write(frame)

    else:
        if recording:
            # Останавливаем запись
            recording = False
            out.release()
            print(f"⏹️ Движение закончилось. Видео сохранено")

    # Показываем движение на экране (зеленым цветом там, где движение)
    cv2.imshow('Motion Detection', thresh)
    cv2.imshow('Camera', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Освобождаем ресурсы
cap.release()
if out:
    out.release()
cv2.destroyAllWindows()
print("✅ Программа завершена")
