from flask import Flask, render_template, redirect, request, make_response, jsonify, url_for
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from os import remove


class DataTemplate:
    def get_data(self, tmp_a=False, base_req=False, lk_req=False, reg_req=False):
        data = dict()
        if base_req:
            data.update(self.get_base_data())
        if lk_req:
            t = self.get_lk_data(tmp_a)
            data['user'] = t['user']
            data['errors'].update(t['errors'])
        if reg_req:
            t = self.get_registration_data()
            data['last'].update(t['last'])
            data['errors'].update(t['errors'])
        return data

    def get_base_data(self):
        return {'menu_items': [{'name': 'tablets',
                                'link': '#'},
                               {'name': 'Смартфоны',
                                'link': '#'}],
                'errors': {'authorization': {'password': None,
                                             'login': None,
                                             'other': None,
                                             'any': False}},
                'last': {'authorization': {'password': '',
                                           'login': ''}}
                }

    def get_lk_data(self, tmp_a=False):
        response = dict(get_self_response('/users/{}'.format((tmp_a if tmp_a else get_authorization())['id']),
                                          method='GET'))
        if response['success']:
            return {'user': response['user'],
                    'errors': {'change_profile_info': {'name': None,
                                                       'surname': None,
                                                       'email': None,
                                                       'check_password': None,
                                                       'new_password': None,
                                                       'photo': None}},
                    }

    def get_sign_in_data(self):
        pass

    def get_registration_data(self):
        data = {'errors': {'registration': {}},
                'last': {'registration': {}}
                }
        for i in ['name', 'surname', 'email', 'login', 'password']:
            data['errors']['registration'][i] = None
            data['last']['registration'][i] = ''
        return data


host = '127.0.0.1'
port = 8080

admin_id = -1
admin_login = "admin"
admin_password = "admin"

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'myOwn_secretKey_nobodyCan_hackIt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///all_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

HOME = '/re_restore'

D = DataTemplate()


def get_authorization(tmp_id=None, tmp_login=None, tmp_password=None, img=False):
    a = {'id': tmp_id if tmp_id else request.cookies.get('userID'),
         'login': tmp_login if tmp_login else request.cookies.get('userLogin'),
         'password': tmp_password if tmp_password else request.cookies.get('userPassword')}
    if img and a['id']:
        try:
            a.update(UserModel.query.filter_by(id=a['id']).first().to_dict(photo_req=True))
        except Exception as e:
            print("Get authorization photo Error:\t", e)
            sign_out()
            for i in a:
                a[i] = None
    return a


def verify_curr_admin():
    a = get_authorization()
    if a and a['id'] == admin_id and a['login'] == admin_login and \
            a['password'] == admin_password:
        return True
    return False


def verify_authorization(admin=False):
    if admin and verify_curr_admin():
        return True
    a = get_authorization()
    try:
        user = UserModel.query.filter_by(id=a['id']).first()
        if user and a['login'] == user.login and \
                check_password_hash(user.password, a['password']):
            return True
        sign_out()
        return False
    except:
        sign_out()
        return False


def render(template, a=None, **kwargs):
    authorization = a if a else get_authorization(img=True)
    if (not a) and (not verify_authorization(admin=True)):
        sign_out()
        return render_template(template, authorization=get_authorization(), **kwargs)
    return render_template(template, authorization=authorization, **kwargs)


class GoodsModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    name = db.Column(db.String(70), nullable=False)
    description = db.Column(db.String(2000), nullable=False)
    short_description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    photos = db.Column(db.String(500))

    def __repr__(self):
        return '<Goods {} {} {}руб {}шт>'.format(self.id, self.name, self.price, self.count)

    def to_dict(self, id_req=True, name_req=True, description_req=False,
                short_description_req=True, price_req=True, count_req=False, photos_req=False):
        d = dict()
        if id_req:
            d['id'] = self.id
        if name_req:
            d['name'] = self.name
        if description_req:
            d['description'] = self.description
        if short_description_req:
            d['short_description'] = self.short_description
        if price_req:
            d['price'] = self.price
        if count_req:
            d['count'] = self.count
        if photos_req:
            d['photos'] = [photo.strip() for photo in self.photos.split(';')]
        return d


class UserModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    subscription = db.Column(db.SMALLINT, default=1)
    photo = db.Column(db.String(100), default="NoPhoto.jpg")

    def __repr__(self):
        return '<User {} {} {} {}>'.format(self.id, self.login, self.name, self.surname)

    def to_dict(self, id_req=True, name_req=False, surname_req=False,
                email_req=False, login_req=False, photo_req=False,
                subscr_req=False, all_req=False):
        if all_req:
            id_req, name_req, surname_req, email_req, login_req, photo_req, subscr_req = tuple(True for i in range(7))
        d = dict()
        if id_req:
            d['id'] = self.id
        if name_req:
            d['name'] = self.name
        if surname_req:
            d['surname'] = self.surname
        if email_req:
            d['email'] = self.email
        if login_req:
            d['login'] = self.login
        if subscr_req:
            d['subscription'] = self.subscription
        if photo_req:
            d['photo'] = 'static/profiles/' + self.photo
        return d


class Authorization(Resource):
    # Аутентификация
    def get(self):
        errors = {'already_authorized': False,
                  'password': None,
                  'login': None,
                  'other': None}
        try:
            if verify_authorization(admin=True):
                errors['already_authorized'] = True
                return make_success(False, errors=errors)

            parser = reqparse.RequestParser()
            for arg in ('login', 'password'):
                parser.add_argument(arg)
            args = parser.parse_args()
            login = args['login']
            password = args['password']

            if not (login.strip() and password.strip()):
                for field, filled in (('login', login.strip()), ('password', password.strip())):
                    if not filled:
                        errors[field] = "Поле дожно быть заполнено."
                return make_success(False, errors=errors)

            if login == admin_login and password == admin_password:
                return make_success(admin_id, errors=errors)

            user = UserModel.query.filter_by(login=login).first()
            if user:
                if check_password_hash(user.password, password):
                    return make_success(user.id, errors=errors)
                errors['password'] = "Неправильный пароль."
            else:
                errors['login'] = "Логин не найден в системе."
        except Exception as e:
            print("Authorization (API) Error:\t", e)
            errors['other'] = "Ошибка сервера."
        return make_success(False, errors=errors)

    # Регистрация
    def post(self):
        all_fields = ['name', 'surname', 'email', 'login', 'password']
        errors = dict()
        for field in all_fields + ['other']:
            errors[field] = None

        try:
            if get_authorization()['id']:
                return make_success(False)

            parser = reqparse.RequestParser()
            for field in all_fields + ['subscription']:
                parser.add_argument(field)
            args = dict(parser.parse_args())

            # проверка на пустоту
            for field in all_fields:
                if not args[field]:
                    errors[field] = 'Поле должно быть заполнено.'
                else:
                    args[field] = args[field].strip()
            if any(val for val in errors.values()):
                return make_success(False, errors=errors)

            # на занятый логин
            if (args['login'] == admin_login or
                    UserModel.query.filter_by(login=args['login']).first()):
                errors['login'] = "Логин занят другим пользователем. Придумайте другой."

            # на длину полей (для базы данных)
            if len(args['name']) > 80:
                errors['name'] = "Слишком длинное имя (максимум 80 символов)."
            if len(args['surname']) > 80:
                errors['surname'] = "Слишком длинная фамилия (максимум 80 символов)."
            if len(args['email']) > 120:
                errors['email'] = "Слишком длинный e-mail (максимум 120 символов)."
            if len(args['login']) > 80 and not errors['login']:
                errors['login'] = "Слишком длинный логин (максимум 80 символа)."
            if len(args['password']) > 100:
                errors['password'] = "Слишком длинный пароль (максимум 100 символов)."
            if len(args['password']) < 3:
                errors['password'] = "Слишком простой пароль (не менее 3 символов)."

            if any(err for err in errors.values()):
                return make_success(False, errors=errors)

            args['password'] = generate_password_hash(args['password'])
            args['subscription'] = 1 if args['subscription'] else 0

            new_user = UserModel(**args)
            db.session.add(new_user)
            db.session.commit()

            return make_success(new_user.id, errors=errors)
        except Exception as e:
            print("Registration (API) Error:\t", e)
            errors['other'] = "Ошибка сервера."
            return make_success(False, errors=errors)


class User(Resource):
    def get(self, user_id):
        user_id = int(user_id)
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return make_success(False)
        return make_success(user=user.to_dict(all_req=True))

    def put(self, user_id, request_data=False):
        errors = {'name': None,
                  'surname': None,
                  'email': None,
                  'check_password': None,
                  'new_password': None,
                  'photo': None}
        try:
            if request_data:
                args = dict()
                args.update(request.args)
                args.update(request.files)
            else:
                parser = reqparse.RequestParser()
                for arg in ('name', 'surname', 'email', 'check_password', 'new_password', 'subscription', 'photo'):
                    parser.add_argument(arg)
                args = parser.parse_args()
            user = UserModel.query.filter_by(id=int(user_id)).first()

            if args['photo']:
                photo_name = None
                try:
                    ext = args['photo'][-1].filename.split('.')[-1]
                    if ext.lower() in ['png', 'jpg', 'jpeg']:
                        photo_name = '{}.{}'.format(user.id, 'png')
                        args['photo'][-1].save('static/profiles/' + photo_name)
                        user.photo = photo_name
                        db.session.commit()
                    else:
                        raise TypeError
                except Exception as e:
                    print("Save photo during changing user info Error:\t", e)
                    if photo_name:
                        remove(photo_name)
                        errors['photo'] = "Ошибка при загрузке фото."

            if 'check_password' not in args or not args['check_password']:
                if 'photo' in args and args['photo']:
                    return make_success(errors=errors)
                errors['check_password'] = "Введите старый пароль для подтверждения."
                return make_success(False, errors=errors)

            if not check_password_hash(user.password, args['check_password']):
                errors['check_password'] = "Старый пароль введен неверно."
                return make_success(False, errors=errors)

            if args['name'] and args['name'] != user.name:
                if len(args['name']) > 80:
                    errors['name'] = "Слишком длинное имя (> 80 символов)."
                else:
                    user.name = args['name'].strip()
            if args['surname'] and args['surname'] != user.surname:
                if len(args['surname']) > 80:
                    errors['surname'] = "Слишком длинная фамилия (> 80 символов)."
                else:
                    user.surname = args['surname'].strip()
            if args['email'] and args['email'] != user.email:
                if len(args['email']) > 120:
                    errors['email'] = "Слишком длинный e-mail (> 120 символов)."
                else:
                    user.email = args['email'].strip()
            if args['new_password']:
                if len(args['new_password']) > 100:
                    errors['new_password'] = "Слишком длинный пароль (> 100 символов)."
                elif len(args['new_password']) < 3:
                    errors['new_password'] = "Слишком простой пароль (< 3 символов)."
                else:
                    user.password = generate_password_hash(args['new_password'].strip())

            user.subscription = 1 if args['subscription'] else 0

            db.session.commit()
            return make_success(errors=errors)
        except Exception as e:
            print("Change user info Error:\t", e)
            return make_success(False, 'Server error')

    # def delete(self, user_id):
    #     user_id = int(user_id)
    #     if get_authorization()['id'] == admin_id:
    #         exist = user_exist(user_id)
    #         if not exist[0]:
    #             return success(False, 'User not found')
    #         try:
    #             user = UserModel.query.filter_by(id=user_id).first()
    #             db.session.delete(user)
    #             db.session.commit()
    #             return success()
    #         except:
    #             return success(False, 'Server error')
    #     return success(False, 'Access error')


def make_success(state=True, message='', **kwargs):
    data = {'success': state if state else False}
    if message:
        data['message'] = message
    data.update(kwargs)
    return data


@app.route('/re_restore', methods=["GET", "POST"])
def re_restore():
    t = 'Добро пожаловать в Re_restore!'
    data = D.get_data(base_req=True)

    data.update(
        {'slides': [url_for('static', filename='main_banners/{}.png'.format(i + 1)) for i in range(4)],
         'len_slides': 4,
         'goods': [{'name': 'iPad 2017, 32GB, Wi-Fi only, Silver',
                    'short-description': 'Уникальный планшет, который вы должны купить',
                    'price': 25000,
                    'image': url_for('static', filename='goods/tablets/ipad_2017/1.png')},
                   {'name': 'iPad 2017, 32GB, Wi-Fi only, Silver',
                    'short-description': 'Уникальный планшет, который вы должны купить',
                    'price': 25000,
                    'image': url_for('static', filename='goods/tablets/ipad_2017/1.png')},
                   {'name': 'iPad 2017, 32GB, Wi-Fi only, Silver',
                    'short-description': 'Уникальный планшет, который вы должны купить',
                    'price': 25000,
                    'image': url_for('static', filename='goods/tablets/ipad_2017/1.png')},
                   {'name': 'iPad 2017, 32GB, Wi-Fi only, Silver',
                    'short-description': 'Уникальный планшет, который вы должны купить',
                    'price': 25000,
                    'image': url_for('static', filename='goods/tablets/ipad_2017/1.png')},
                   {'name': 'iPad 2017, 32GB, Wi-Fi only, Silver',
                    'short-description': 'Уникальный планшет, который вы должны купить',
                    'price': 25000,
                    'image': url_for('static', filename='goods/tablets/ipad_2017/1.png')}]
         }
    )
    if request.method == "GET":
        return render('index.html', title=t, data=data)

    elif request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('index.html', t, data)


@app.route('/re_restore/<string:category>')
def category(category):
    return render('/goods-category')


@app.route('/re_restore/<string:category>/<int:goods_id>')
def goods(category, goods_id):
    return render('/goods')


def sign_in(page, t, data, ready_data=None):
    if get_authorization()['id']:
        return redirect('/lk')

    response = get_self_response('/authorization', data=ready_data if ready_data else request.form, method='GET')
    if response['success']:
        a = get_authorization(response['success'], request.form['login'], request.form['password'], img=True)
        if page in ('sign-up.html', 'lk.html'):
            data = D.get_data(base_req=True, lk_req=True, tmp_a=a)
            page = 'lk.html'
        resp = make_response(render(page, a=a, title=t, data=data))
        resp.set_cookie('userID', str(a['id']))
        resp.set_cookie('userLogin', str(a['login']))
        resp.set_cookie('userPassword', str(a['password']))
    else:
        data['errors']['authorization'].update(response['errors'])
        data['errors']['authorization']['any'] = True
        data['last']['authorization']['login'] = request.form['login']
        data['last']['authorization']['password'] = request.form['password']
        resp = make_response(render(page, title=t, data=data))
    return resp


@app.route('/sign-out')
def sign_out():
    resp = make_response(redirect(HOME))
    for cookie in ('userID', 'userLogin', 'userPassword'):
        resp.set_cookie(cookie, '', expires=0)
    return resp


@app.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    if get_authorization()['id']:
        return redirect('/lk')

    t = 'Регистрация'
    data = D.get_data(base_req=True, reg_req=True)

    if request.method == "GET":
        return render('sign-up.html', t=t, data=data)

    elif request.method == "POST":
        form = dict(request.form)
        for i in form:
            if type(form[i]) is list:
                form[i] = form[i][-1]
        if 'sign-in' in form:
            return sign_in('sign-up.html', t, data)

        response = get_self_response('/authorization', data=form, method='POST')
        if response['success']:
            return sign_in('lk.html', t='Успешно', data=data, ready_data={'login': form['login'],
                                                                          'password': form['password']})
        else:
            data['errors']['registration'].update(response['errors'])
            data['last']['registration'].update(form)
    return render('sign-up.html', t=t, data=data)


@app.route('/lk', methods=["GET", "POST"])
def lk():
    t = "Личный кабинет"
    if verify_curr_admin():
        return redirect('/lk-admin')
    elif verify_authorization():
        data = D.get_data(base_req=True, lk_req=True)
        if request.method == 'GET':
            return render("lk.html", title=t, data=data)

        form = dict(request.form)
        if request.method == 'POST':
            if 'changeUserInfoBtn' in form:
                response = dict(get_self_response('/users/{}'.format(get_authorization()['id']),
                                                  data=form, method='PUT'))
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
                return render("lk.html", title=t, data=data)
            elif 'photo' in request.files:
                response = userAPI.put(get_authorization()['id'], request_data=True)
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
                return render("lk.html", title=t, data=data)
            return server_error()

    return redirect(HOME)


@app.route('/lk-admin', methods=["GET", "POST"])
def lk_admin_general():
    t = "Личный кабинет (ADMIN)"
    if verify_curr_admin():
        data = D.get_data(base_req=True)

        return render('lk-admin.html', title=t, data=data)
    elif verify_authorization():
        return redirect('/lk')
    return redirect(HOME)


@app.route('/lk-admin/<string:section>', methods=["GET", "POST"])
def lk_admin_section(section):
    pass


def get_self_response(url, data={}, method='GET'):
    try:
        if method == 'GET':
            return requests.get('http://{}:{}'.format(host, port) + url, json=data).json()
        if method == 'POST':
            return requests.post('http://{}:{}'.format(host, port) + url, json=data).json()
        if method == 'DELETE':
            return requests.delete('http://{}:{}'.format(host, port) + url, json=data).json()
        if method == 'PUT':
            return requests.put('http://{}:{}'.format(host, port) + url, json=data).json()
    except:
        return {'success': False}


def error(err=520, message='Что-то пошло не так :('):
    data = D.get_data(base_req=True)
    data.update({'message': message, 'type': err})
    return render('error.html', data=data)


@app.errorhandler(401)
def access_error(err=None):
    return error(401, 'Отказано в доступе :(')


@app.errorhandler(404)
def not_found(err=None):
    return error(404, 'Страница не найдена :(')


@app.errorhandler(500)
def server_error(err=None):
    return error(500, 'Ошибка сервера :(')


@app.route('/')
@app.route('/index')
def index():
    return redirect(HOME)


userAPI = User()

if __name__ == '__main__':
    db.create_all()

    api.add_resource(Authorization, '/authorization')
    api.add_resource(User, '/users/<int:user_id>')

    app.run(port=port, host=host)
