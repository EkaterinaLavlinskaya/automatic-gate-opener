 Настройка SMS
1. Регистрация на[ sms.ru](https://sms.ru/)
Зарегистрируйся на[ sms.ru](https://sms.ru/)

Получи API-ключ в личном кабинете

Пополни баланс (для отправки SMS)

2. Замени в коде:
python
SMS_API_KEY = "ВАШ_API_КЛЮЧ"
YOUR_PHONE = "+7XXXXXXXXXX"


🔄 Для реальной работы с SMS
В реальной системе нужно настроить webhook для получения ответов. SMS.ru предоставляет API для получения входящих SMS:

python
# Альтернативный вариант: периодический опрос входящих SMS
def check_incoming_sms():
    url = "https://sms.ru/sms/status"
    params = {"api_id": SMS_API_KEY, "json": 1}
    response = requests.get(url, params=params)
    data = response.json()
    
    # Обработка входящих SMS
    if data.get("status") == "OK":
        for sms in data.get("sms", []):
            if sms.get("text", "").strip() == "1":
                # Пользователь ответил "да"
                open_gate()

Система готова к работе! 🚀

