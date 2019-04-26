from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import json
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sdflgnern3j242pn'
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

session_storage = {
    'Регистрация': False,
    'Вход': False
}

SKILL_ID = 'a38dddc2-b89a-4a22-8b93-f70ff53d31ed'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(80), unique=False, nullable=False)

    def __repr__(self):
        return f'<User {self.id} {self.username}>'


class Marker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    map = db.Column(db.Integer, unique=False, nullable=False)
    coord = db.Column(db.String(80), unique=False, nullable=False)
    description = db.Column(db.String(1024), unique=False, nullable=True)

    user_id = db.Column(db.Integer,
                        db.ForeignKey('user.id'),
                        nullable=False)
    user = db.relationship('User', backref=db.backref('marker', lazy=True))

    def __repr__(self):
        return f'<Marker {self.id} {self.user_id}>'


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
        res['response']['text'] = 'Зарегистрируйтесь или войдите'
        res['response']['buttons'] = [
            {
                'title': 'Регистрация',
                'hide': True
            },
            {
                'title': 'Вход',
                'hide': True
            },
            {
                'title': 'Справка',
                'hide': True
            }
        ]

        return

    res['request']['buttons'] = [
        {
            'title': 'Справка',
            'hide': True
        }
    ]

    req_text = req['request']['original_utterance']

    # Регистрация
    if req_text == 'Регистрация':
        res['response']['text'] = 'Введите имя и пароль через пробел'
        session_storage['Регистрация'] = True

        return

    if session_storage.get('Регистрация'):
        if len(req_text.split()) != 2:
            res['response']['text'] = 'Эрмил вас не понял, введите еще раз'
            return

        username, password = req_text.split()

        # Проверка на существование
        user = User.query.filter_by(username=username).first()
        if user:
            res['response']['text'] = 'Имя занято, придумайте другое'
            return

        password_hash = generate_password_hash(password)

        user = User(
            username=username,
            password_hash=password_hash
        )

        db.session.add(user)
        db.session.commit()

        session_storage['Регистрация'] = False

        res['response']['text'] = 'Вы зарегистрировались, можете войти'
        res['response']['buttons'] += [
            {
                'title': 'Вход',
                'hide': True
            }
        ]

        session_storage.pop('Регистрация')

        return

    # Вход
    if req_text == 'Вход':
        res['response']['text'] = 'Введите имя и пароль через пробел'
        session_storage['Вход'] = True

        return

    if session_storage.get('Вход'):
        if len(req_text.split()) != 2:
            res['response']['text'] = 'Эрмил вас не понял, введите еще раз'
            return

        username, password = req_text.split()
        user = User.query.filter_by(username=username).first()

        if not user:
            res['response']['text'] = 'Такого пользователя нет, введите еще раз'
            return

        # Отмечаем пользователя
        session_storage['username'] = user.username
        session_storage['user_id'] = user.id

        res['response']['text'] = 'Вы вошли'
        res['response']['buttons'] += [
            {
                'title': 'Создать метку',
                'hide': True
            },
            {
                'title': 'Показать метку',
                'hide': True
            }
        ]

        session_storage.pop('Вход')

        return

    # Создание метки
    if req_text == 'Создать метку':
        res['response']['text'] = 'Введите широту и долготу через пробел'
        session_storage['Создание метки'] = True

        return

    # Ввод координат
    if session_storage.get('Создание метки') and\
            not session_storage.get('Метка'):
        if len(req_text.split()) != 2:
            res['response']['text'] = 'Эрмил вас не понял, введите еще раз'
            return

        coord = req_text.split()

        map = set_marker(coord)

        res['response']['text'] = 'Введите описание'

        session_storage['Метка'] = {
            'yandex_id': map,
            'coord': ' '.join(coord)
        }

        return

    # Ввод описания, создание метки
    if session_storage.get('Метка') and\
            session_storage.get('Метка'):
        map = session_storage['Метка']['yandex_id']

        marker = Marker(
            map=map,
            coord=session_storage['Метка']['coord'],
            description=req_text,
            user_id=session_storage['user_id']
        )

        db.session.add(marker)
        db.session.commit()

        res['response']['text'] = f'Метка {map} создана'
        res['response']['buttons'] += [
            {
                'title': 'Показать метку',
                'hide': True
            },
            {
                'title': 'Создать метку',
                'hide': True
            }
        ]

        session_storage.pop('Метка')
        session_storage.pop('Создание метки')

        return

    # Показываем метку
    if req_text == 'Показать метку':
        res['response']['text'] = 'Введите id метки'
        session_storage['Показать метку'] = True

        return

    if session_storage.get('Показать метку'):
        marker = Marker.query.filter_by(map=req_text).first()

        if not marker:
            res['response']['text'] = 'Такой метки нет, введите еще раз'
            return

        res['response']['text'] = 'Карта'
        res['response']['card'] = {
            'type': 'BigImage',
            'image_id': marker.map,
            'description': marker.description,
            'title': marker.map
        }

        return

    res['response']['text'] = 'Эрмил вас не понял'


def set_marker(coord):
    """Вовзращает id карты с указанным координатами из Яндекс.Диалоги"""

    # Меняем широту и долготу из-за static api
    coord = ','.join(reversed(coord))

    # Получаем изображение карты с меткой
    url_static_api = 'https://static-maps.yandex.ru/1.x/'

    params = {
        'l': 'sat,skl',
        'll': coord,
        'pt': f'{coord},pm2dgl'
    }

    map = requests.get(url_static_api, params).content

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
