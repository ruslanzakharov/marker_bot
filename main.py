from flask import Flask, request
import logging
import json
import requests

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

session_storage = {}

SKILL_ID = 'a38dddc2-b89a-4a22-8b93-f70ff53d31ed'


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        'response': {
            'end_session': False
        },
        'session': request.json['session'],
        'version': request.json['version']
    }

    handle_dialog(response, request.json)

    logging.info('Response: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    """Обрабатывает запрос"""

    if req['session']['new']:
        res['response']['text'] = 'Введите координаты'

    req_text = req['request']['original_utterance']
    if not session_storage:
        session_storage['закладка1'] = req_text

        return

    if session_storage:
        map = set_marker(session_storage['закладка1'])

        res['card'] = {
            'type': 'BigImage',
            'image_id': map,
        }

        return


def set_marker(coord):
    """Создает карту с меткой"""

    # Получаем изображение карты с меткой
    url_static_api = 'https://static-maps.yandex.ru/1.x/'

    params = {
        'l': 'sat,skl',
        'll': coord,
    }

    map = requests.get(url_static_api, params)
    logging.info(f'Request: {map}')

    # Размещаем изображение в Яндекс.Диалоги и получаем id
    url_ya_dialogs = f'https://dialogs.yandex.net/api/v1/skills/{SKILL_ID}/images'

    files = {'file': map}
    headers = {
        'Authorization': 'OAuth AQAAAAATNA8lAAT7o-7tTToNjUOljgg7VeV1pdY'
    }

    id = requests.post(url_ya_dialogs, files=files, headers=headers).json()

    return id['image']['id']


if __name__ == '__main__':
    app.run()
