import logging
import os
import time
from http import HTTPStatus
from pprint import pprint

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

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
    check = []
    for name_token, token in tokens_dict.items():
        if not token:
            check.append(name_token)
    if check:
        message = f'Отсутствует переменная(ые) окружения: {", ".join(check)}'
        logging.critical(message)
        raise AssertionError(message)


def send_message(bot: TeleBot, message: str) -> bool:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение отправлено - {message}')
        return True
    except ApiException as error:
        logging.error(f'Сбой при отправке сообщения: {error}')
        return False


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    api_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    logging.info(f'Запрос к эндпоинту: {api_params["url"]}')
    try:
        response = requests.get(**api_params)
    except requests.RequestException as error:
        raise f'Ошибка при запросе к API: {error}'
    if response.status_code != HTTPStatus.OK:
        raise f'Получен код ответа - {response.status_code}. Ожидается 200'
    return response.json()


def check_response(response: dict) -> dict:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не словарь')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ответе API нет списка домашних работ')
    return response.get('homeworks')


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе ее статус."""
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework.get('status')]
    except KeyError as error:
        raise f'Неверный статус домашней работы {error}'
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    last_status = ''
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('Получен пустой список домашних работ')
                continue
            status_home_work = parse_status(homeworks[0])
            if (status_home_work != last_status and
                    send_message(bot, status_home_work)):
                last_status = status_home_work
                timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_status != message and send_message(bot, message):
                last_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    current_file = os.path.abspath(__file__)
    log_file_path = current_file + '.log'
    file_handler = logging.FileHandler(log_file_path)
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s - %(lineno)d'
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    main()
