# bot.py
import requests

def send_message(chat_id, text):
    bot_token = '7182933265:AAF_xSFjmwltWCHDH1LUg9GRTIIWVmT0e6k'  # Замените на ваш токен
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    print(f"Sending message with payload: {payload}")  # Отладка
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print(f"Response: {response.json()}")  # Отладка
    except requests.RequestException as e:
        print(f"Ошибка при отправке сообщения: {e}")