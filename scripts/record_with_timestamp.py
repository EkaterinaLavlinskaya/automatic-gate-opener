import cv2
import datetime


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print(" Камера не найдена. Попробуй изменить номер камеры.")
    exit()

# Параметры видео
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
filename = f"C:/Users/Денис/Downloads/recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))

print(f" Запись: {filename}")
print(" Нажми 'q' для остановки")

while True:
    ret, frame = cap.read()
    if not ret:
        print(" Ошибка захвата кадра")
        break
    
    # Добавляем время на кадр
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    cv2.imshow('Camera', frame)
    out.write(frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
print(" Готово! Видео сохранено.")
