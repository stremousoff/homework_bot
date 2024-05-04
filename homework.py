import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
payload = {'from_date': 1549962000}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    tokens_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name_token, token in tokens_dict.items():
        if not token:
            message = f'Отсутствует переменная окружения: {name_token}'
            logging.critical(message)
            raise AssertionError(message)


def send_message(bot: TeleBot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    payload['from_date'] = timestamp
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as e:
        raise logging.error(f'Ошибка при запросе к API: {e}')
    if response.status_code != HTTPStatus.OK:
        raise logging.error('Неверный статус код')
    return response.json()


def check_response(response: dict) -> dict:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise logging.error('Ответ API не словарь')
    elif 'homeworks' not in response:
        raise logging.error('Отсутствует ключ "homeworks"')
    elif not isinstance(response['homeworks'], list):
        raise logging.error('В ответе API нет списка домашних работ')
    else:
        if response.get('homeworks'):
            return response.get('homeworks')[0]


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе ее статус."""
    if homework:
        try:
            homework_name = homework['homework_name']
        except KeyError:
            raise logging.error('Отсутствует ключ "homework_name"')
        try:
            verdict = HOMEWORK_VERDICTS[homework.get('status')]
        except KeyError:
            raise logging.error(
                f'Неизвестный статус домашней работы {homework.get("status")}'
            )
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.debug('не получен статус домашней работы')


def main():
    """Основная логика работы бота."""
    check_tokens()
    last_status = ''
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        response = get_api_answer(timestamp)
        homework = check_response(response)
        status_home_work = parse_status(homework)
        try:
            if status_home_work and status_home_work != last_status:
                send_message(bot, status_home_work)
                last_status = status_home_work
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
        time.sleep(RETRY_PERIOD)
        timestamp = int(time.time())


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    main()
