from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import json
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite: ///main.db'
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
    username = db.Column(db.String(80), unigue=True, nullable=False)
    password_hash = db.Column(db.String(80), unique=False, nullable=False)

    def __repr__(self):
        return f'<User {self.id} {self.username}>'


class Marker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    map = db.Column(db.Integer(80), unique=False, nullable=False)
    coords = db.Column(db.String(80), unique=False, nullable=False)
    description = db.Column(db.String(1024), unigue=False, nullable=False)

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
                'payload': {'Регистрация': True},
                'hide': True
            },
            {
                'title': 'Вход',
                'payload': {'Вход': True},
                'hide': True
            }
        ]

        return

    req_text = req['request']['original_utterance']

    # Регистрация
    if req_text == 'Регистрация' and req['request']['payload']:
        res['response']['text'] = 'Введите имя и пароль через пробел'
        session_storage['Регистрация'] = True

        return

    if session_storage['Регистрация']:
        username, password = req_text.split()

        password_hash = generate_password_hash(password)

        user = User(
            username=username,
            password_hash=password_hash
        )

        db.session.add(user)
        db.session.commit()

        session_storage['Регистрация'] = False

        res['response']['text'] = 'Вы зарегистрировались, можете войти'
        res['response']['buttons'] = [
            {
                'title': 'Вход',
                'payload': {'Вход': True},
                'hide': True
            }
        ]

    # Вход
    if req_text == 'Вход' and req['request']['payload']:
        res['response']['text'] = 'Введите имя и пароль через пробел'
        session_storage['Войти'] = True

        return

    if session_storage['Войти']:
        username, password = req_text.split()
        user = User.query.filter_by(username=username).first()

        if user:
            session['username'] = user.username

        res['response']['text'] = 'Вы вошли'
        res['response']['buttons'] = [
            {
                'title': 'Вход',
                'payload': {'Вход': True},
                'hide': True
            }
        ]

    map = set_marker(req_text)

    res['response']['text'] = 'Фото'
    res['response']['card'] = {
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


def registration():
    pass


def login():
    pass


db.create_all()

if __name__ == '__main__':
    app.run()
