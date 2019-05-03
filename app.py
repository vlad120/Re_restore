"""
    Version 1.3.0 (03.05.2019)
    Mironov Vladislav
"""

from flask import Flask, render_template, redirect, request, make_response
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from os import remove, listdir, makedirs, rmdir, path, rename
from shutil import copyfile
from json import loads, dumps
from random import randrange
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'myOwn_secretKey_nobodyCan_hackIt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///all_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

NO_GOODS_PHOTO = '/static/goods/NoPhoto.jpg'
NO_PROFILE_PHOTO = '/static/profiles/NoPhoto.jpg'


def get_authorization(tmp_login=None, tmp_password=None, img=False, params=None):
    """
        Получение авторизации из cookie-файлов / преобразование полученных данных:
        tmp-аргументы - когда надо получить временную авторизацию (если cookie ещё не настроены);
        params - из получение данных от параметров для API (формат: {'authorization': 'login;password'}).
    """
    check_need = False
    if params and type(params) is dict and 'login' in params and 'password' in params:
        tmp_login, tmp_password = params['login'], params['password']
        check_need = True

    tmp = tmp_login and tmp_password
    a = {'login': tmp_login if tmp else request.cookies.get('userLogin'),
         'password': tmp_password if tmp else request.cookies.get('userPassword'),
         'admin_authorization': False}

    user = UserModel.query.filter_by(login=a['login']).first()
    if user:
        a['id'] = user.id
    elif a['login'] == ADMIN_LOGIN and a['password'] == ADMIN_PASSWORD:
        a['id'] = ADMIN_ID
        a['admin_authorization'] = True
    else:
        a['id'], a['login'], a['password'] = None, None, None

    if check_need and not verify_authorization(a=a, admin=True):
        a['id'], a['login'], a['password'] = None, None, None

    if img and a['id']:
        user = UserModel.query.filter_by(id=a['id']).first()
        if user:
            a.update(user.to_dict(photo_req=True))
            a['photo'] = a['photo']
        else:
            a['photo'] = '/static/profiles/NoPhoto.jpg'
    return a


def verify_curr_admin(a=None):
    a = a if a else get_authorization()
    try:
        if int(a['id']) == ADMIN_ID and \
                a['login'] == ADMIN_LOGIN and \
                a['password'] == ADMIN_PASSWORD:
            return True
    except:
        pass
    return False


def verify_authorization(admin=False, a=None):
    if admin and verify_curr_admin(a):
        return True
    a = a if a else get_authorization()
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


def get_folder(goods, sl=True, category=None):
    """
        Получить директорию конкретного товара в файловой системе:
        sl - нужен ли '/' в конце возвращаемого пути;
        category - использутся, когда нужно получить другой, новый путь.
    """
    name = "_".join(goods.name[:10].split())  # замена пробелов в имени
    category = (category if category else goods.category).strip(' /')
    return 'static/goods/{}/{}'.format(category, name) + ('/' if sl else '')


def optimize_params(params):
    for arg in params:
        try:
            if type(params[arg]) is list:
                params[arg] = params[arg][0]
        except:
            pass


class GoodsModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(15000), nullable=False)
    short_description = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(150), nullable=False)
    photos = db.Column(db.String(500), default=NO_GOODS_PHOTO)

    def __repr__(self):
        return '<GoodsModel {} {} {}руб {}шт>'.format(self.id, self.name, self.price, self.count)

    def to_dict(self, id_req=True, name_req=True, description_req=False,
                short_description_req=False, card_description_req=False,
                price_req=True, count_req=True, category_req=True,
                full_category_req=False, full_link_req=False,
                photo_req=False, photos_req=False):
        d = dict()
        if id_req:
            d['id'] = self.id
        if name_req:
            d['name'] = self.name
        if description_req:
            d['description'] = self.description
        if short_description_req:
            d['short_description'] = self.short_description
        if card_description_req:
            d['card_description'] = " ".join(self.short_description[:100].split()[:-1]).rstrip('.,/;:!') + " ..."
        if price_req:
            d['price'] = self.price
        if count_req:
            d['count'] = self.count
        if category_req:
            d['category'] = self.category
        if full_category_req:
            c = CategoryModel.query.filter_by(name=self.category).first()
            if c:
                d['full_category'] = c.to_dict()
        if full_link_req:
            d['full_link'] = '/{}/{}'.format(self.category.strip(' /'), self.id)
        if photo_req:
            photos = self.photos.strip(';').split(';')
            if len(photos) == 1 and photos[0] == NO_GOODS_PHOTO:
                d['photo'] = NO_GOODS_PHOTO
            else:
                d['photo'] = '/{}/{}'.format(get_folder(self), photos[0])
        if photos_req:
            photos = self.photos.strip(';').split(';')
            if len(photos) == 1 and photos[0] == NO_GOODS_PHOTO:
                d['photos'] = [NO_GOODS_PHOTO]
                d['len_photos'] = 1
            else:
                folder = '/' + get_folder(self)
                d['photos'] = [folder + photo.strip(' /') for photo in photos]
                d['len_photos'] = len(photos)
        return d


class CategoryModel(db.Model):
    name = db.Column(db.String(150), unique=True, primary_key=True)
    rus_name = db.Column(db.String(150), unique=True)

    def __repr__(self):
        return '<CategoryModel {}>'.format(self.name)

    def to_dict(self, name_req=True, rus_name_req=True, link_req=True):
        d = dict()
        if name_req:
            d['name'] = self.name
        if rus_name_req:
            d['rus_name'] = self.rus_name
        if link_req:
            d['link'] = '/' + self.name.strip('/')
        return d


class OrderModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    total = db.Column(db.Float, nullable=False)
    goods = db.Column(db.String, nullable=False)
    status = db.Column(db.String(10), default="processing")
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    user = db.relationship('UserModel', backref=db.backref('OrderModel'))

    def __repr__(self):
        return '<OrderModel {} {}руб>'.format(self.id, self.total)

    def to_dict(self, id_req=True, total_req=True, goods_req=True,
                status_req=True, user_req=True):
        d = dict()
        if id_req:
            d['id'] = self.id
        if total_req:
            d['total'] = self.total
        if goods_req:
            d['goods'] = loads(self.goods)
        if status_req:
            d['status'] = self.status
        if user_req:
            d['user'] = self.user.to_dict(login_req=True)
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
    basket = db.Column(db.String, default={'basket': []})

    def __repr__(self):
        return '<UserModel {} {} {} {}>'.format(self.id, self.login, self.name, self.surname)

    def to_dict(self, id_req=True, name_req=False, surname_req=False,
                email_req=False, login_req=False, photo_req=False,
                subscr_req=False, all_req=False):
        if all_req:
            id_req, name_req, surname_req, email_req, login_req, photo_req, subscr_req = (True for _ in range(7))
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
            d['photo'] = '/static/profiles/' + self.photo
        return d


class DataTemplate:
    """
        Получение унифицированных данных для шаблонов html страниц:
        get_data - 'конструктор' нужных данных,
                   собирает все воедино изходя из потребностей для данной страницы.
    """
    def get_data(self, a=None, base_req=False, main_req=False,
                 lk_req=False, lk_admin_req=False, reg_req=False,
                 edit_goods_req=False, basket_req=False, order_req=False):
        """
            a - временная авторизация, необходима при запросе закрытых данных;
            req-аргументы - страницы, для которых надо собрать данные.
        """
        data = dict()
        try:
            if base_req:
                data.update(self.get_base_data())
            if main_req:
                data.update(self.get_main_data())
            if lk_req:
                t = self.get_lk_data(a)
                data['user'] = t['user']
                data['orders'] = t['orders']
                data['errors'].update(t['errors'])
            if lk_admin_req:
                t = self.get_lk_admin_data(a)
                data['errors'].update(t.pop('errors'))
                data.update(t)
            if reg_req:
                t = self.get_registration_data()
                data['last'].update(t['last'])
                data['errors'].update(t['errors'])
            if edit_goods_req:
                data['errors'].update(self.get_edit_goods_data()['errors'])
            if basket_req:
                data.update(self.get_basket_data(a))
            if order_req:
                t = self.get_order_data(a)
                data['order_data'] = t['order_data']
                data['errors']['order'] = t['errors']['order']
            return data
        except Exception as e:
            logging.error("Data template get Error:\t{}".format(e))
            return None

    def get_base_data(self, anyway=False):
        try:
            api_response = basketAPI.get('curr')
            basket = [[int(k) for k in g][0] for g in api_response['basket']] if api_response['success'] else []
            len_basket = len(api_response['basket']) if api_response['success'] else None
            return {'menu_items': [c.to_dict() for c in CategoryModel.query.all()],
                    'len_basket': len_basket,
                    'basket': basket,
                    'errors': {'authorization': {'password': None,
                                                 'login': None,
                                                 'other': None,
                                                 'any': False}},
                    'last': {'authorization': {'password': '',
                                               'login': ''}}
                    }
        except Exception as e:
            logging.error("Get base data template Error:\t{}".format(e))
            if anyway:
                return {'menu_items': [],
                        'len_basket': None,
                        'basket': [],
                        'errors': {'authorization': {'password': None,
                                                     'login': None,
                                                     'other': None,
                                                     'any': False}},
                        'last': {'authorization': {'password': '',
                                                   'login': ''}}
                        }

    def get_main_data(self):  # главная страница
        try:
            interesting_goods = '10'
            api_response = goodsAPI.get('random', params={'n': interesting_goods})
            if api_response['success']:
                goods = api_response['goods']
                slides = list(filter(lambda f: f != '.DS_Store', listdir("static/main_slides")))
                return {'slides': ['static/main_slides/{}'.format(slide) for slide in slides],
                        'len_slides': len(slides),
                        'goods': goods
                        }
        except Exception as e:
            logging.error("Get main data template Error:\t{}".format(e))

    def get_lk_data(self, a=None):
        try:
            a = a if a else get_authorization()
            user_api_response = userAPI.get(a['id'], a=a)
            order_api_response = orderAPI.get('user', a=a, params={'user_id': str(a['id'])})
            if user_api_response['success'] and order_api_response['success']:
                return {'user': user_api_response['user'],
                        'orders': order_api_response['orders'],
                        'errors': {'change_profile_info': {'name': None,
                                                           'surname': None,
                                                           'email': None,
                                                           'check_password': None,
                                                           'new_password': None,
                                                           'photo': None},
                                   'edit_order': None},
                        }
        except Exception as e:
            logging.error("Get lk data template Error:\t{}".format(e))

    def get_lk_admin_data(self, a=None):
        try:
            a = a if a else get_authorization()
            goods_response = goodsAPI.get('all', a=a)
            orders_response = orderAPI.get('all', a=a)
            users_response = userAPI.get('all', a=a)
            data = {'curr_category': 'goods',
                    'goods': goods_response['goods'] if goods_response['success'] else [],
                    'orders': orders_response['orders'] if orders_response['success'] else [],
                    'users': users_response['users'] if users_response['success'] else [],
                    'errors': {'get_data': {'goods': None if goods_response['success'] else goods_response['message'],
                                            'orders': None if orders_response['success'] else orders_response['message'],
                                            'users': None if users_response['success'] else users_response['message']},
                               'add_goods': {}},
                    'last': {'add_goods': {}}
                    }
            for i in ['name', 'description', 'short_description',
                      'price', 'count', 'category']:
                data['errors']['add_goods'][i] = None
                data['last']['add_goods'][i] = ''
            return data
        except Exception as e:
            logging.error("Get lk-admin data template Error:\t{}".format(e))

    def get_registration_data(self):
        try:
            data = {'errors': {'registration': {}},
                    'last': {'registration': {}}
                    }
            for i in ['name', 'surname', 'email', 'login', 'password']:
                data['errors']['registration'][i] = None
                data['last']['registration'][i] = ''
            return data
        except Exception as e:
            logging.error("Get registration data template Error:\t{}".format(e))

    def get_edit_goods_data(self):
        return {'errors': {'edit_goods': {'rus_category': None,
                                          'category': None,
                                          'name': None,
                                          'price': None,
                                          'count': None,
                                          'short_description': None,
                                          'description': None,
                                          'add_photo': None,
                                          'delete_photo': None}}
                }

    def get_basket_data(self, a=None):
        a = a if a else get_authorization()
        if a:
            try:
                api_response = basketAPI.get('curr')
                basket = [[(int(i), int(g[i])) for i in g][0] for g in api_response['basket']]
                goods = [goodsAPI.get(g[0])['data']['goods'] for g in basket]
                for i in range(len(goods)):
                    goods[i]['count'] = basket[i][1]
                if api_response['success']:
                    return {'basket_data': {'goods': goods,
                                            'total': sum(g['price'] * g['count'] for g in goods)}}
            except Exception as e:
                logging.error("Get basket data template Error:\t{}".format(e))
                return {}

    def get_order_data(self, a=None):
        a = a if a else get_authorization()
        if a:
            try:
                api_response = basketAPI.get('curr')
                basket = [[(int(i), int(g[i])) for i in g][0] for g in api_response['basket']]
                goods = [goodsAPI.get(g[0])['data']['goods'] for g in basket]
                for i in range(len(goods)):
                    goods[i]['count'] = basket[i][1]
                if api_response['success']:
                    return {'order_data': {'goods': goods,
                                           'total': sum(g['price'] * g['count'] for g in goods)
                                           },
                            'errors': {'order': None}
                            }
            except Exception as e:
                logging.error("Get basket data template Error:\t{}".format(e))
                return {}


class AuthorizationAPI(Resource):
    # Авторизация
    def get(self, r=None, request_data=None):
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
            args = dict(parser.parse_args())
            if request_data:
                args.update(request_data)

            login = args['login']
            password = args['password']

            if not (login.strip() and password.strip()):
                for field, filled in (('login', login.strip()), ('password', password.strip())):
                    if not filled:
                        errors[field] = "Поле дожно быть заполнено."
                return make_success(False, errors=errors)

            if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
                return make_success(ADMIN_ID, errors=errors)

            user = UserModel.query.filter_by(login=login).first()
            if user:
                if check_password_hash(user.password, password):
                    return make_success(user.id, errors=errors)
                errors['password'] = "Неправильный пароль."
            else:
                errors['login'] = "Логин не найден в системе."
        except Exception as e:
            logging.error("AuthorizationAPI Error:\t{}".format(e))
            errors['other'] = "Ошибка сервера."
        return make_success(False, errors=errors)

    # Регистрация нового пользователя
    def post(self, r=None, request_data=None):
        all_fields = ['name', 'surname', 'email', 'login', 'password']
        errors = dict()
        for field in all_fields + ['other']:
            errors[field] = None

        try:
            if get_authorization()['id']:
                return make_success(False, message="Access error")

            parser = reqparse.RequestParser()
            for arg in all_fields + ['subscription']:
                parser.add_argument(arg)
            args = dict(parser.parse_args())
            if request_data:
                for i in request_data:
                    if i in args:
                        args[i] = request_data[i]

            login = args['login']
            password = args['password']

            # проверка на пустоту
            for field in all_fields:
                if not args[field] and args[field] is not 'subscription':
                    errors[field] = 'Поле должно быть заполнено.'
                else:
                    args[field] = args[field].strip()
            if any(val for val in errors.values()):
                return make_success(False, message="Empty fields", errors=errors)

            # на занятый логин
            if (login == ADMIN_LOGIN or
                    UserModel.query.filter_by(login=login).first()):
                errors['login'] = "Логин занят другим пользователем. Придумайте другой."

            # на длину полей (для базы данных)
            if len(args['name']) > 80:
                errors['name'] = "Слишком длинное имя (максимум 80 символов)."
            if len(args['surname']) > 80:
                errors['surname'] = "Слишком длинная фамилия (максимум 80 символов)."
            if len(args['email']) > 120:
                errors['email'] = "Слишком длинный e-mail (максимум 120 символов)."
            if len(login) > 80 and not errors['login']:
                errors['login'] = "Слишком длинный логин (максимум 80 символа)."
            if len(password) > 100:
                errors['password'] = "Слишком длинный пароль (максимум 100 символов)."
            if len(password) < 3:
                errors['password'] = "Слишком простой пароль (не менее 3 символов)."

            if any(err for err in errors.values()):
                return make_success(False, errors=errors)

            args['password'] = generate_password_hash(password)
            args['subscription'] = 1 if args['subscription'] else 0

            new_user = UserModel(**args)
            db.session.add(new_user)
            db.session.commit()

            return make_success(new_user.id, errors=errors)
        except Exception as e:
            logging.error("RegistrationAPI Error:\t{}".format(e))
            errors['other'] = "Ошибка сервера."
            return make_success(False, message="Server error", errors=errors)


class UserAPI(Resource):
    """ API для получения / редактирования / удаления данных пользователей. """
    def get(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        # получение полных данных конкретного пользователя
        if arg.isdigit():
            user_id = int(arg)
            user = UserModel.query.filter_by(id=user_id).first()
            # проверка на существование
            if not user:
                return make_success(False, message="User {} doesn't exist".format(user_id))
            # проверка на собственника учетной записи / админа
            if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                return make_success(False, message="Access Error")
            return make_success(user=user.to_dict(all_req=True))

        # получение кратких данных всех пользователей (админ)
        if arg == 'all':
            if not verify_curr_admin(a):
                return make_success(False, message='Access Error')
            try:
                return make_success(users=[i.to_dict(name_req=True, surname_req=True,
                                                     email_req=True, login_req=True) for i in
                                           UserModel.query.all()])
            except Exception as e:
                logging.error("UserAPI Error (get all):\t{}".format(e))
                return make_success(False, message='Server Error')
        return make_success(False, message='Bad request')

    def put(self, r, a=None, params=dict(), request_data=None):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            errors = {'name': None,
                      'surname': None,
                      'email': None,
                      'check_password': None,
                      'new_password': None,
                      'photo': None}
            try:
                user_id = int(arg)
                parser = reqparse.RequestParser()
                for arg in ('name', 'surname', 'email', 'check_password', 'new_password', 'subscription', 'photo'):
                    parser.add_argument(arg)
                args = parser.parse_args()
                if request_data:
                    args.update(request_data)

                user = UserModel.query.filter_by(id=user_id).first()
                if not user:
                    return make_success(False, message="User {} doesn't exist".format(user_id))

                # проверка на собственника учетной записи / админа
                if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                    return make_success(False, message="Access Error")

                # редактирование фото
                if 'photo' in args and args['photo']:
                    photo_name = None
                    try:
                        ext = args['photo'].filename.split('.')[-1]
                        if ext.lower() in ['png', 'jpg', 'jpeg']:
                            photo_name = '{}.{}'.format(user.id, 'png')
                            args['photo'].save('static/profiles/' + photo_name)
                            user.photo = photo_name + '?' + str(randrange(1000000000))
                            db.session.commit()
                        else:
                            raise TypeError
                    except Exception as e:
                        logging.error("Save photo (change user info) Error:\t{}".format(e))
                        if photo_name:
                            remove(photo_name)
                            errors['photo'] = "Ошибка при загрузке фото."

                # проверка на ввод подтверждающего пароля
                # для возможности дальнейшего редактирования личных данных
                if 'check_password' not in args or not args['check_password']:
                    if 'photo' in args and args['photo']:  # если редактировалось только фото
                        return make_success(errors=errors)
                    errors['check_password'] = "Введите старый пароль для подтверждения."
                    return make_success(False, errors=errors)

                # проверка подтверждающего пароля
                if not check_password_hash(user.password, args['check_password']):
                    errors['check_password'] = "Старый пароль введен неверно."
                    return make_success(False, errors=errors)

                # обработка поступивших данных
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

                user.subscription = 1 if args['subscription'] else 0  # подписка на новости

                db.session.commit()
                return make_success(errors=errors)
            except Exception as e:
                logging.error("Change user info Error:\t{}".format(e))
                return make_success(False, 'Server error')

        return make_success(False, 'Bad request')

    def delete(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            user_id = int(arg)
            # проверка на собственника учетной записи / админа
            if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                return make_success(False, message="Access Error")
            try:
                user = UserModel.query.filter_by(id=user_id).first()
                if user:
                    # удаляем фото профиля
                    photo = 'static/profiles/{}.png'.format(arg)
                    if path.exists(photo):
                        remove(photo)
                    # удаляем все заказы пользователя
                    for order in OrderModel.query.filter_by(user_id=user_id).all():
                        db.session.delete(order)
                    db.session.delete(user)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="User {} doesn't exist".format(user_id))
            except Exception as e:
                logging.error("User delete Error:\t{}".format(e))
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


class GoodsAPI(Resource):
    """ API для получения / реадктирования информации о товаре, создания / удаления товаров. """
    def get(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        # полная информация об одном товаре
        if arg.isdigit():
            goods_id = int(arg)
            try:
                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if not goods:
                    return make_success(False, message="Goods {} doesn't exist".format(goods_id))
                if 'short' in params and params['short']:
                    return make_success(data={'goods': goods.to_dict()})
                elif 'short_with_description' in params and params['short_with_description']:
                    return make_success(data={'goods': goods.to_dict(short_description_req=True,
                                                                     full_link_req=True)})
                return make_success(data={'goods': goods.to_dict(description_req=True,
                                                                 short_description_req=True,
                                                                 photos_req=True,
                                                                 count_req=True,
                                                                 full_category_req=True,
                                                                 full_link_req=True)})
            except Exception as e:
                logging.error("GoodsAPI Error (get {}):\t{}".format(goods_id, e))
                return make_success(False, message='Server Error')

        # краткая информация обо всех товарах для админа
        if arg == 'all':
            if verify_curr_admin(a):
                try:
                    return make_success(goods=[i.to_dict(full_link_req=True, short_description_req=True)
                                               for i in reversed(GoodsModel.query.all())])
                except Exception as e:
                    logging.error("GoodsAPI Error (get all):\t{}".format(e))
                    return make_success(False, message='Server Error')
            return make_success(False, message='Access Error')

        # 1 или несколько рандомных товаров
        if arg == 'random':
            try:
                n = int(params['n']) if 'n' in params else 1
                # множество перемешанных товаров (которые есть в наличии)
                goods = set(filter(lambda g: g.count > 0, (i for i in GoodsModel.query.all())))
                # обрезка до нужного количества и
                # преобразование каждого товара в словарь
                goods = list(g.to_dict(photo_req=True, full_link_req=True,
                                       card_description_req=True,
                                       short_description_req=True) for g in list(goods)[:n])
                return make_success(goods=goods)
            except Exception as e:
                logging.error("GoodsAPI Error (get random):\t{}".format(e))
                return make_success(False, message='Server Error')

        # все товары данной категории
        if arg == 'category':
            category = CategoryModel.query.filter_by(name=params['category']).first()
            if category:
                try:
                    goods = GoodsModel.query.filter_by(category=category.name).all()
                    # сортировка товаров
                    if 'sort' in params:
                        if params['sort'] == 'NEW':
                            goods.sort(key=lambda g: g.id, reverse=True)
                        elif params['sort'] == 'CHE':
                            goods.sort(key=lambda g: int(g.price))
                        elif params['sort'] == 'EXP':
                            goods.sort(key=lambda g: int(g.price), reverse=True)
                    return make_success(goods=list(filter(lambda g: g['count'] > 0,
                                                          [i.to_dict(full_link_req=True,
                                                           card_description_req=True,
                                                           photo_req=True) for i in goods])),
                                        category=category.to_dict())
                except Exception as e:
                    logging.error("GoodsAPI Error (get category {}):\t{}".format(arg, e))
                    return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def put(self, r, a=None, params=dict(), request_data=None):
        # перемещение данных товара в файловой системе
        def move_goods(goods, new_category, errors=dict()):
            e = None
            try:
                old_category = CategoryModel.query.filter_by(name=goods.category).first()
                old_folder = get_folder(goods, category=old_category.name, sl=False)
                new_folder = get_folder(goods, category=new_category.name, sl=False)
                if not path.exists(new_folder):
                    makedirs(new_folder)
                if path.exists(old_folder):
                    photos = goods.photos.split(';')
                    for item in listdir(old_folder):
                        if item in photos:
                            copyfile(old_folder + '/' + item, new_folder + '/' + item)
                            remove(old_folder + '/' + item)
                    old_folder_items = list(filter(lambda f: f != '.DS_Store',
                                                   listdir(old_folder)))
                    if not old_folder_items:
                        rmdir(old_folder)
                        old_category_folder = "/".join(old_folder.split('/')[:-1])
                        old_category_folder_items = list(filter(lambda f: f != '.DS_Store',
                                                                listdir(old_category_folder)))
                        if not old_category_folder_items:
                            rmdir(old_category_folder)
            except Exception as e:
                logging.error("GoodsAPI Error "
                              "(move folder while edit goods {} category):\t{}".format(goods.id, e))
                errors['category'] = "Move folder error"
            if not e:
                try:
                    if not path.exists(new_folder):
                        makedirs(folder)
                        logging.info("GoodsAPI Error "
                                     "(folder wasn't created while edit goods {} category)"
                                     " - solved!".format(goods.id))

                    if len(GoodsModel.query.filter_by(category=old_category.name).all()) == 1:
                        db.session.delete(old_category)
                        db.session.commit()
                    if not CategoryModel.query.filter_by(name=new_category.name).first():
                        db.session.add(new_category)
                        db.session.commit()
                    goods = GoodsModel.query.filter_by(id=goods_id).first()
                    goods.category = args['category']
                    db.session.commit()
                except Exception as e:
                    logging.error("GoodsAPI Error "
                                  "(edit goods {} DB category):\t{}".format(goods.id, e))
                    errors['category'] = "Edit DB error"
            return errors

        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            errors = D.get_edit_goods_data()['errors']['edit_goods']
            try:
                goods_id = int(arg)
                parser = reqparse.RequestParser()
                for arg in errors.keys():
                    parser.add_argument(arg)
                args = parser.parse_args()
                if request_data:
                    args.update(request_data)

                if not any([args[i] for i in args]):
                    return make_success(message="Empty request", errors=errors)

                for i in args:
                    if type(args[i]) is str:
                        args[i] = args[i].strip(' /')

                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if not goods:
                    return make_success(False, message="Goods {} doesn't exist".format(goods_id))

                # проверка на / админа
                if not verify_curr_admin(a):
                    return make_success(False, message="Access Error")

                unknown_err = "Неизвестная ошибка. Проверьте правильность ввода."

                # изменение названия товара
                if args['name'] and args['name'] != goods.name:
                    try:
                        if len(args['name']) > 80:
                            m = "Название должно быть не более 80 символов ({}).".format(len(args['name']))
                            errors['name'] = m
                        elif '/' in args['name']:
                            m = "Название не может содержать символ '/'."
                            errors['name'] = m
                        else:
                            old_folder = get_folder(goods, sl=False)
                            goods.name = args['name']
                            if path.exists(old_folder):
                                new_folder = get_folder(goods, sl=False)
                                rename(old_folder, new_folder)
                            db.session.commit()
                    except:
                        errors['name'] = unknown_err

                # категории товара
                curr_category = CategoryModel.query.filter_by(name=goods.category).first()
                if args['category'] and args['category'] != goods.category:
                    try:
                        if len(args['category']) > 150:
                            m = "Категория ({}) должна быть не более 150 символов.".format(len(args['category']))
                            errors['category'] = m
                        elif '/' in args['category']:
                            m = "Категория не может содержать символ '/' в названии."
                            errors['category'] = m
                        else:
                            # если нужно изменить и русскую категорию
                            if args['rus_category'] != curr_category.rus_name:
                                if args['rus_category'] and len(args['rus_category']) > 150:
                                    m = "Категория должна быть не более 150 символов."
                                    errors['rus_category'] = m
                                elif '/' in args['rus_category']:
                                    m = "Категория не может содержать символ '/' в названии."
                                    errors['rus_category'] = m
                                else:
                                    check_category = CategoryModel.query.filter_by(name=args['category']).first()
                                    check_rus_category = CategoryModel.query.filter_by(rus_name=args['rus_category'])
                                    check_rus_category = check_rus_category.first()
                                    # если русская категория существует в БД
                                    if check_rus_category:
                                        # и если переданная системная категория соответствует ей
                                        if check_rus_category.name == args['category']:
                                            # т.е. если и русская и системная категории есть в БД
                                            new_category = CategoryModel(name=args['category'],
                                                                         rus_name=args['rus_category'])
                                            move_goods(goods, new_category, errors=errors)  # перемещаем данные + БД
                                        else:
                                            m = "Русская категория должна быть уникальной для каждой " \
                                                "системной категории (конфликт: {}).".format(check_rus_category.name)
                                            errors['rus_category'] = m
                                    # если системная категория есть в БД
                                    elif check_category:
                                        # на русскую категорию проверку делать уже бессмысленно (сделано выше)
                                        m = "Русская категория должна быть уникальной для каждой " \
                                            "системной категории (конфликт: {}).".format(check_category.name)
                                        errors['rus_category'] = m
                                    else:
                                        # т.е. если ни русской категории, ни системной нет в БД
                                        new_category = CategoryModel(name=args['category'],
                                                                     rus_name=args['rus_category'])
                                        move_goods(goods, new_category)  # создаем директорию и перемещаем данные + БД
                            else:
                                # если в текущей категории присутствуют другие товары
                                if len(GoodsModel.query.filter_by(category=goods.category).all()) > 1:
                                    m = "Изменять системную категорию можно только вкупе с русской, " \
                                        "либо убедившишь, что товар единственный в данной категории."
                                    errors['category'] = m
                                else:
                                    # т.е. если это единственный товар категории,
                                    # пытаемся переместить данные товара, удалить старую категорию,
                                    # создать новую и изменить все в БД
                                    new_category = CategoryModel(name=args['category'],
                                                                 rus_name=curr_category.rus_name)
                                    move_goods(goods, new_category)  # перемещаем данные
                    except Exception as e:
                        logging.error("GoodsAPI Error "
                              "(set goods {} category while edit info):\t{}".format(goods.id, e))
                        errors['category'] = unknown_err

                elif args['rus_category']:
                    try:
                        # есть ли различия между новой и текущей
                        if curr_category and args['rus_category'] != curr_category.rus_name:
                            if len(args['rus_category']) > 150:
                                m = "Категория должна быть не более 150 символов."
                                errors['rus_category'] = m
                            elif '/' in args['rus_category']:
                                m = "Категория не может содержать символ '/' в названии."
                                errors['rus_category'] = m
                            else:
                                category = CategoryModel.query.filter_by(rus_name=args['rus_category']).first()
                                # существует ли уже новая категория
                                if category:
                                    m = "Данная русския категория занята другой системной ({}).".format(category.name)
                                    errors['rus_category'] = m
                                # если в текущей системной категории находится только 1 товар (этот)
                                # и тем самым изенение не повлияет на остальных
                                elif len(GoodsModel.query.filter_by(category=curr_category.name).all()) == 1:
                                    # меняем русское название системной категории
                                    curr_category.rus_name = args['rus_category']
                                    db.session.commit()
                                else:
                                    # иначе зашита от перезаписи русских категорий остальных товаров
                                    m = "В системной категории данного товара находятся другие товары – " \
                                        "защита от случайного переименования русской категории других товаров."
                                    errors['rus_category'] = m
                    except Exception as e:
                        logging.error("GoodsAPI Error "
                                      "(set goods {} rus category while edit info):\t{}".format(goods.id, e))
                        errors['rus_category'] = unknown_err

                # цены товара
                if args['price']:
                    if type(args['price']) is int or str(args['price']).isdigit():
                        price = int(args['price'])
                        if price != goods.price:
                            goods.price = price
                            db.session.commit()
                    else:
                        errors['price'] = "Неверный формат."

                # количества товара
                if args['count']:
                    if type(args['count']) is int or str(args['count']).isdigit():
                        count = int(args['count'])
                        if count != goods.count:
                            goods.count = count
                            db.session.commit()
                    else:
                        errors['count'] = "Неверный формат."

                # Краткого описания
                if args['short_description']:
                    try:
                        if len(args['short_description']) > 120:
                            errors['short_description'] = "Краткое описание должно быть не более 120 символов."
                        elif args['short_description'] != goods.short_description:
                            goods.short_description = args['short_description']
                            db.session.commit()
                    except Exception as e:
                        logging.error("GoodsAPI Error (edit short description while edit info):\t{}".format(e))
                        errors['short_description'] = unknown_err

                # Полного описания
                if args['description']:
                    try:
                        if len(args['description']) > 15000:
                            errors['description'] = "Описание должно быть не более 15000 символов."
                        elif args['description'] != goods.description:
                            goods.description = args['description']
                            db.session.commit()
                    except Exception as e:
                        logging.error("GoodsAPI Error (edit description while edit info):\t{}".format(e))
                        errors['short_description'] = unknown_err

                # удаление фото
                if args['delete_photo']:
                    try:
                        if args['delete_photo'].strip('/') != NO_GOODS_PHOTO.strip('/'):
                            photo = args['delete_photo'].split('/')[-1]
                            # проверка на случай, если фото уже нет в папке
                            if photo in listdir():
                                remove(photo)
                            # в любом случае, удаляем его из списка фотографий товара
                            photos = goods.photos.split(';')
                            for i in range(photos.count(photo)):
                                photos.remove(photo)
                            goods.photos = ";".join(photos) if photos else NO_GOODS_PHOTO
                            db.session.commit()
                    except Exception as e:
                        logging.error("GoodsAPI Error (delete photo while edit info):\t{}".format(e))
                        errors['delete_photo'] = "Ошибка сервера при удалении фото."

                # добавление фотографий
                if args['add_photo'] and any(filter(lambda p: bool(p), args['add_photo'])):
                    try:
                        if type(args['add_photo']) is not list:
                            args['add_photo'] = [args['add_photo']]
                        goods_photos = goods.photos.split(';')
                        args['add_photo'] = list(reversed(args['add_photo']))
                        for i in range(len(args['add_photo'])):
                            photo = args['add_photo'][i]
                            # проверка на случайное совпадение имен фотографий
                            if photo.filename in goods_photos + listdir():
                                m = "Некоторые фотографии не были загружены, т.к. произошел конфликт имен"
                                errors['add_photo'] = m
                                continue
                            try:
                                ext = photo.filename.split('.')[-1]
                                if ext.lower() in ['png', 'jpg', 'jpeg']:
                                    folder = get_folder(goods, sl=False)
                                    if not path.exists(folder):
                                        makedirs(folder)
                                    photo.save('{}/{}'.format(folder, photo.filename))
                                    photos = goods.photos.split(';')
                                    if len(photos) == 1 and photos[0] == NO_GOODS_PHOTO:
                                        goods_photos = [photo.filename]
                                    else:
                                        goods_photos.append(photo.filename)
                                    goods.photos = ";".join(goods_photos)
                                    db.session.commit()
                                else:
                                    raise TypeError
                            except Exception as e:
                                logging.error("GoodsAPI Error (edit info, save photo):\t{}".format(e))
                                if photo:
                                    url = '{}/{}'.format(get_folder(goods, sl=False), photo.filename)
                                    if path.exists(url):
                                        remove(url)
                                errors['add_photo'] = "Ошибка при загрузке некоторых фото."
                    except Exception as e:
                        logging.error("GoodsAPI Error (load photo while edit info):\t{}".format(e))
                        errors['add_photo'] = "Ошибка при загрузке фото."
                db.session.commit()
                return make_success(errors=errors)
            except Exception as e:
                logging.error("Change goods ({}) info Error:\t{}".format(arg, e))
                return make_success(False, 'Server error')

        return make_success(False, 'Bad request')

    def post(self, r, a=None, params=dict(), request_data=None):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        # размещение нового товара
        if arg == 'new':
            if not verify_curr_admin(a):
                return make_success(False, message="Access error")

            all_fields = ['name', 'description', 'short_description',
                          'price', 'count', 'category', 'rus_category']
            errors = dict()
            for field in all_fields:
                errors[field] = None

            try:
                parser = reqparse.RequestParser()
                for arg in all_fields:
                    parser.add_argument(arg)
                args = dict(parser.parse_args())
                if request_data:
                    for i in request_data:
                        if i in args:
                            args[i] = request_data[i].strip() if type(request_data[i]) is str else request_data[i]

                # проверка на пустоту
                err = False
                for field in all_fields:
                    if not args[field]:
                        errors[field] = 'Поле должно быть заполнено.'
                        err = True
                if err:
                    return make_success(False, message="Empty fields", errors=errors)

                for i in args:
                    if type(args[i]) is str:
                        args[i] = args[i].strip(' /')

                # длина полей (для базы данных)
                if len(args['name']) > 80:
                    errors['name'] = "Название ({}) должно быть не более 80 символов.".format(len(args['name']))
                if len(args['description']) > 15000:
                    errors['description'] = "Описание ({}) должно " \
                                            "быть не более 15000 символов.".format(len(args['description']))
                if len(args['short_description']) > 120:
                    errors['short_description'] = "Краткое описание ({}) должно " \
                                                  "быть не более 120 символов.".format(len(args['short_description']))
                if len(args['category']) > 150:
                    errors['category'] = "Категория ({}) не должна " \
                                         "превышать 150 символов.".format(len(args['category']))
                if len(args['rus_category']) > 150:
                    errors['rus_category'] = "Категория ({}) не должна " \
                                             "превышать 150 символов.".format(len(args['rus_category']))

                # содержание запрещенных символов
                if '/' in args['name']:
                    errors['name'] = "Название не может содержать символ '/'."
                if '/' in args['category']:
                    errors['category'] = "Категория не может содержать символ '/'."
                if '/' in args['rus_category']:
                    errors['rus_category'] = "Категория не может содержать символ '/'."

                if any(err for err in errors.values()):
                    return make_success(False, message="Too much data", errors=errors)

                if not CategoryModel.query.filter_by(name=args['category']).first():
                    c = CategoryModel(name=args['category'], rus_name=args['rus_category'])
                    db.session.add(c)
                args.pop('rus_category')

                # правильный формат количества и цены
                err = False
                for val_type, field in ((int, 'count'), (int, 'price')):
                    try:
                        args[field] = val_type(args[field])
                    except ValueError:
                        errors[field] = "Неверный формат."
                        err = True
                if err:
                    return make_success(False, message="Type Error", errors=errors)

                goods = GoodsModel(**args)
                db.session.add(goods)
                db.session.commit()
                return make_success(goods.id, errors=errors)
            except Exception as e:
                logging.error("GoodsAPI Error (add goods):\t{}".format(e))
                return make_success(False, message="Server error", errors=errors)

        return make_success(False, message='Bad request')

    def delete(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            # проверка на админа
            if not verify_curr_admin(a):
                return make_success(False, message="Access Error")
            try:
                goods = GoodsModel.query.filter_by(id=arg).first()
                if goods:
                    db.session.delete(goods)
                    db.session.commit()
                    # удаление данных товара с файловой системы
                    photos = goods.photos.split(';')
                    folder = get_folder(goods, sl=False)
                    if path.exists(folder):
                        for item in listdir(folder):
                            if item in photos:
                                remove('{}/{}'.format(folder, item))
                        # если пустая директория товара, удаляем ее за собой
                        if not list(filter(lambda f: f != '.DS_Store', listdir(folder))):
                            rmdir(folder)
                            category = "/".join(folder.split('/')[:-1])
                            # если пустая директория категории, удаляем и ее
                            if not list(filter(lambda f: f != '.DS_Store', listdir(category))):
                                rmdir(category)
                    return make_success()
                return make_success(False, message="Goods doesn't exist")
            except Exception as e:
                logging.error("Goods delete Error:\t\t{}".format(e))
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


class SearchAPI(Resource):
    """ API для поиска товаров в БД. """
    def get(self, r, a=None, params=dict()):
        symbols = ' ,.;:"\'!@#$%^&*()'

        def by_name(name, end=False):
            name = name.lower()
            full = []
            great_part = []
            small_part = []
            consist = []
            for goods in GoodsModel.query.all():
                goods_name = goods.name.lower()
                if goods_name == name:
                    # если в наличии
                    if goods.count > 0:
                        full.insert(0, goods.id)  # добавляем в начало
                    else:
                        # при отстствии добавляем в конец
                        full.append(goods.id)
                elif name in goods_name:
                    if len(goods.name) - len(name) < 10:
                        if goods.count > 0:
                            great_part.insert(0, goods.id)
                        elif a['admin_authorization']:
                            great_part.append(goods.id)
                    elif name in [w.strip(symbols) for w in goods_name.split()]:
                        if goods.count > 0:
                            small_part.insert(0, goods.id)
                        elif a['admin_authorization']:
                            small_part.append(goods.id)
                else:
                    # множества слов в названиях
                    name_words = {w.strip(symbols) for w in name.split()}
                    goods_name_words = {w.strip(symbols) for w in goods_name.split()}
                    # разница между (количеством слов в искомом названии) и
                    # (количеством пересечений этих слов со словами названия товара)
                    n = len(name_words & goods_name_words)
                    if n:
                        diff = len(name_words) - n
                        if diff <= 2 and goods.count > 0:
                            consist.insert(0, goods.id)
                        elif diff <= 4 and (goods.count > 0 or a['admin_authorization']):
                            consist.append(goods.id)
            # объединяем и возвращаем найденное в порядке соответствия
            if end:
                return full + great_part + consist + small_part
            return [full, great_part, consist, small_part]

        def by_description(text, end=False):
            text = text.lower()
            full = []
            great_part = []
            small_part = []
            consist = []
            text_words = {w.strip(symbols) for w in text.split()}  # множество слов в тексте
            len_text_words = len(text_words)
            for goods in GoodsModel.query.all():
                description = (goods.short_description + ' ' + goods.description).lower()
                description_words = {w.strip(symbols) for w in
                                     description.split()}  # множество слов в описании
                if text in description_words:
                    if goods.count > 0 or a['admin_authorization']:
                        small_part.append(goods.id)
                else:
                    n = len(text_words & description_words)
                    if n:
                        diff = len_text_words - n
                        # если разница между количеством слов в тексте
                        # и количеством их пересечений со словами из описания маленькая
                        # (т.е. большинство слов в тексте найдено в описании)
                        if diff <= (len_text_words // 5) * 3:
                            if goods.count > 0 or a['admin_authorization']:
                                consist.append(goods.id)
            # объединяем и возвращаем найденное в порядке соответствия
            if end:
                return full + great_part + consist + small_part
            return [full, great_part, consist, small_part]

        # умное избавление от одинаковых результатов
        # + если надо, преврящаем все goods_id в данные для карточек
        def remove_same(lst):
            new = []
            for item in lst:
                if item not in new:
                    new.append(item)
            if need_cards:
                new = list(map(lambda g_id: GoodsModel.query.filter_by(id=g_id).first().to_dict(
                    full_link_req=True,
                    card_description_req=True,
                    photo_req=True), new))
            return new

        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)
        arg = str(r).lower().strip(' /')
        need_cards = params['cards'] if 'cards' in params else False
        max_count = params['max'] if 'max' in params else 10

        # поиск по артиклу
        if arg == 'id':
            try:
                if 'goods_id' not in params:
                    return make_success(False, message="Bad request")
                goods = GoodsModel.query.filter_by(id=params['goods_id']).first()
                if goods:
                    return make_success(goods=[goods.id])
                return make_success(goods=[])
            except Exception as e:
                logging.error("SearchAPI Error (get by id):\t{}".format(e))
                return make_success(False, message='Server Error')

        # поиск по названию
        if arg == 'name':
            try:
                if 'name' not in params:
                    return make_success(False, message="Bad request")
                result = remove_same(by_name(params['name'], end=True))[:max_count]
                return make_success(goods=result)
            except Exception as e:
                logging.error("SearchAPI Error (get by name):\t{}".format(e))
                return make_success(False, message='Server Error')

        # поиск по описанию
        if arg == 'description':
            try:
                if 'description' not in params:
                    return make_success(False, message="Bad request")
                result = remove_same(by_name(params['description'], end=True))[:max_count]
                return make_success(goods=result)
            except Exception as e:
                logging.error("SearchAPI Error (get by description):\t{}".format(e))
                return make_success(False, message='Server Error')

        if arg == 'auto':
            try:
                if 'text' not in params:
                    return make_success(False, message="Bad request")

                # поиск чисел
                result0 = None
                num = list(filter(lambda w: w.strip().isdigit(), params['text'].split()))
                if num:
                    # совпадение числа с id товара
                    result0 = GoodsModel.query.filter_by(id=num[0]).first()

                # получение результов поиска по разным критериям
                result1 = by_name(params['text'])  # по названию
                result2 = by_description(params['text'])  # по всему описанию
                result = []

                # объединение всех результатов в порядке их соответствия запросу
                for i in range(4):
                    result += result1[i]  # сначала всегда найденное по имени
                    result += result2[i]
                if result0:  # если найден товар по id
                    result.insert(0, result0.id)  # добавляем в начало всего найденного
                result = remove_same(result)[:max_count]
                return make_success(goods=result)
            except Exception as e:
                logging.error("SearchAPI Error (get by all parameters):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')


class BasketAPI(Resource):
    """ API для получения корзины, реадктирования / добавления / удаления товаров в ней. """
    def get(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg == 'curr':
            try:
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    return make_success(basket=loads(user.basket)['basket'])
                return make_success(False, "Authorization error")
            except Exception as e:
                logging.error("BasketAPI Error (get):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def put(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            try:
                if a:
                    if not GoodsModel.query.filter_by(id=arg).first():
                        return make_success(False, message="Goods doesn't exist")

                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")

                    basket = loads(user.basket)
                    names = [[k for k in g][0] for g in basket['basket']]
                    if arg not in names:
                        return make_success(False, message="Goods is not in basket")

                    # изменение количества товара в корзине
                    if 'count' in params and (params['count'] == 'all' or
                                              (params['count'].isdigit() and int(params['count']) > 0)):
                        goods = GoodsModel.query.filter_by(id=arg).first()
                        count = int(params['count']) if params['count'].isdigit() else goods.count
                        if not goods:
                            basket['basket'][names.index(arg)].pop(arg)
                            user.basket = dumps(basket)
                            db.session.commit()
                            return make_success(False, message="Goods doesn't exist")
                        if count > goods.count:
                            basket['basket'][names.index(arg)][arg] = goods.count
                            user.basket = dumps(basket)
                            db.session.commit()
                            return make_success(False, message="Value is more than goods count")
                        basket['basket'][names.index(arg)][arg] = count
                        user.basket = dumps(basket)
                        db.session.commit()
                    else:
                        return make_success(False, message="Count error")
                    return make_success()
                return make_success(False, message="Authorization error")
            except Exception as e:
                logging.error("BasketAPI Error (edit):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def post(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            try:
                goods = GoodsModel.query.filter_by(id=arg).first()
                if not goods:
                    return make_success(False, message="Goods doesn't exist")
                # проверка авторизации (админу добавлять товары в корзину нельзя)
                if a and a['id'] != ADMIN_ID:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    basket = loads(user.basket)
                    if arg in [[k for k in g][0] for g in basket['basket']]:
                        return make_success(False, message="Goods has already added", count=goods.count)
                    if 'count' in params:
                        count = int(params['count'])
                        if goods.count < count:
                            return make_success(False, message="Count is more then original")
                        basket['basket'].append({str(arg): count})
                    else:
                        basket['basket'].append({str(arg): 1})
                    user.basket = dumps(basket)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="Authorization error")
            except Exception as e:
                logging.error("BassketAPI Error (add):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def delete(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            try:
                if not GoodsModel.query.filter_by(id=arg).first():
                    return make_success(False, message="Goods doesn't exist")
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    basket = loads(user.basket)
                    names = [[k for k in g][0] for g in basket['basket']]
                    if arg not in names:
                        return make_success(False, message="Goods is not in basket")
                    del basket['basket'][names.index(arg)]
                    user.basket = dumps(basket)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="Authorization error")
            except Exception as e:
                logging.error("BasketAPI Error (delete):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')


class OrderAPI(Resource):
    """ API для получения / размещения / удаления заказов, реадктирования их статусов. """
    def get(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        # получение всех заказов (админ)
        if arg == 'all':
            if not verify_curr_admin(a):
                return make_success(False, message='Access Error')
            try:
                return make_success(orders=list(reversed([i.to_dict() for i in OrderModel.query.all()])))
            except Exception as e:
                logging.error("OrderAPI Error (get all):\t{}".format(e))
                return make_success(False, message='Server Error')
        # получение заказов конкретного пользователя
        if arg == 'user':
            if not verify_authorization(admin=True, a=a):
                return make_success(False, message='Access Error')
            user_id = params['user_id'] if 'user_id' in params else a['id']
            try:
                orders = [i.to_dict()
                          for i in reversed(OrderModel.query.filter_by(user_id=user_id).all())]
                return make_success(orders=orders)
            except Exception as e:
                logging.error("OrderAPI Error (get by user {}):\t{}".format(user_id, e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def post(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg == 'curr':
            try:
                # проверка авторизации (админу делать заказы нельзя)
                if a and a['id'] != ADMIN_ID:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")

                    # получение корзины
                    api_response = basketAPI.get('curr')
                    if not api_response['success'] or not api_response['basket']:
                        return make_success(False, message="Basket get data error")
                    # обработка в удобный вид кортежей [(goods_id, count), ...]
                    basket = [[(int(i), int(g[i])) for i in g][0] for g in api_response['basket']]
                    goods = [GoodsModel.query.filter_by(id=g[0]).first().to_dict(full_link_req=True)
                             for g in basket]
                    errs = []
                    for i in range(len(goods)):
                        # проверка на наличие требуемого количества товаров
                        if goods[i]['count'] < basket[i][1]:
                            # если товар закончился
                            if goods[i]['count'] < 1:
                                if not basketAPI.delete(goods[i]['id'])['success']:
                                    return make_success(False,
                                                        message="Delete goods from basket error "
                                                                "(count value is more original)")
                            # пытаемся изменить количество в корзине
                            if not basketAPI.put(goods[i]['id'], params={'count': 'all'})['success']:
                                return make_success(False,
                                                    message="Edit goods from basket error "
                                                            "(count value is more original)")
                            # при изменении предупреждаем пользвателя об изменениях
                            errs.append(goods[i])
                        else:
                            goods[i]['count'] = basket[i][1]
                    if errs:
                        return make_success(False, message="Goods count error", goods=errs)
                    order = OrderModel(goods=dumps(goods),
                                       total=sum(g['price'] * g['count'] for g in goods),
                                       user_id=user.id)
                    db.session.add(order)
                    user.basket = dumps({'basket': []})  # опустошаем корзину
                    # перебираем заказанные товары
                    for g in goods:
                        db_goods = GoodsModel.query.filter_by(id=g['id']).first()
                        # вычитаем количесвто товара в заказе из БД
                        db_goods.count = db_goods.count - g['count']
                    db.session.commit()
                    return make_success(order_id=order.id)
                return make_success(False, message="Authorization error")
            except Exception as e:
                logging.error("OrderAPI Error (add):\t{}".format(e))
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def delete(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            try:
                order_id = int(arg)
                order = OrderModel.query.filter_by(id=order_id).first()
                if order:
                    # проверка на собственника учетной записи / админа
                    if not (verify_curr_admin(a) or (int(a['id']) == order.user_id and verify_authorization(a=a))):
                        return make_success(False, message="Access Error")
                    db.session.delete(order)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="Order doesn't exist")
            except Exception as e:
                logging.error("Order delete Error:\t{}".format(e))
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')

    def put(self, r, a=None, params=dict()):
        params = params if params else dict(request.args)
        optimize_params(params)
        a = a if a else get_authorization(params=params)

        arg = str(r).lower().strip(' /')
        if arg.isdigit():
            try:
                # редактирование статуса заказа
                if 'status' in params:
                    order_id = int(arg)
                    order = OrderModel.query.filter_by(id=order_id).first()
                    if order:
                        # статусы 'доставлено' и 'выполнено' (только админ)
                        if params['status'] in ['done', 'delivered']:
                            # проверка на админа
                            if not verify_curr_admin(a):
                                return make_success(False, message="Access Error")
                        # отмена заказа (доступно и пользователю, и админу)
                        elif params['status'] == 'cancel':
                            # проверка авторизации
                            if not verify_authorization(a):
                                return make_success(False, message="Access Error")
                        else:
                            # если статус-аргумент не соответствует ожиданиям
                            return make_success(False, message="Bad status")
                        order.status = params['status']
                        db.session.commit()
                        return make_success()
                    return make_success(False, message="Order doesn't exist")
            except Exception as e:
                logging.error("Order put Error:\t{}".format(e))
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


@app.route('/', methods=["GET", "POST"])
def re_restore():
    t = 'Добро пожаловать в Re_restore!'
    data = D.get_data(base_req=True, main_req=True)

    if request.method == "GET":
        return render('index.html', title=t, data=data)

    elif request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('index.html', t, data)

        if 'addToBasket' in request.form:
            api_response = basketAPI.post(request.form['addToBasketGoodsID'])
            if not api_response['success']:
                logging.error("Add to basket error:\t{}".format(api_response['massage']))
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']
            return render('index.html', title=t, data=data)


@app.route('/search/')
def search():
    try:
        if 'text' not in request.args:
            return redirect('/')
        text = request.args['text'].strip()
        data = D.get_base_data()
        data['request'] = text
        data['goods'] = []
        data['empty_request'] = True
        if text:
            data['empty_request'] = False
            api_response = searchAPI.get(r='auto', params={'text': text, 'cards': True, 'max': 15})
            data['goods'] = api_response['goods']
        return render('search.html', title="Поиск", data=data)
    except Exception as e:
        logging.error("User search Error (text: {}):\t{}".format(text, e))
        return server_error()


@app.route('/<string:category>', methods=["GET", "POST"])
def goods_category(category):
    data = D.get_base_data()
    data['sorting'] = request.cookies.get('sorting')
    if not data['sorting']:
        data['sorting'] = 'NEW'

    api_response = goodsAPI.get('category', params={'category': category, 'sort': data['sorting']})
    if not api_response['success']:
        if not CategoryModel.query.filter_by(name=category).first():
            return not_found()
        return server_error()

    data['goods'] = api_response['goods']
    data['full_category'] = api_response['category']

    t = api_response['category']['rus_name']

    form = get_request_data()
    if request.method == "POST":
        if 'sign-in' in form:
            return sign_in('goods-category.html', 'Вход', data)

        if 'addToBasket' in form:
            api_response = basketAPI.post(form['addToBasketGoodsID'])
            if not api_response['success']:
                logging.error("Add to basket error:\t{}".format(api_response['message']))
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']
            return render('goods-category.html', title=t, data=data)

        if 'sorting' in form:
            data['sorting'] = form['sorting']
            api_response = goodsAPI.get('category', params={'category': category, 'sort': data['sorting']})
            if api_response['success']:
                data['goods'] = api_response['goods']
            resp = make_response(render('goods-category.html', title=t, data=data))
            resp.set_cookie('sorting', form['sorting'])
            return resp

    return render('goods-category.html', title=t, data=data)


@app.route('/<string:category>/<int:goods_id>', methods=["GET", "POST"])
def full_goods(category, goods_id):
    if not CategoryModel.query.filter_by(name=category).first():
        return not_found()
    data = D.get_base_data()
    if not data:
        return server_error()

    api_response = goodsAPI.get(goods_id)
    if not api_response['success']:
        return error(message=api_response['message'])
    data.update(api_response['data'])

    t = api_response['data']['goods']['name']

    if request.method == "POST":
        form = get_request_data(files=True)
        if 'sign-in' in form:
            return sign_in('goods.html', t, data)

        if 'addToBasket' in form:
            api_response = basketAPI.post(form['addToBasketGoodsID'])
            if not api_response['success']:
                logging.error("Add to basket error:\t{}".format(api_response['message']))
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']

    return render('goods.html', title=t, data=data)


@app.route('/goods-admin/<int:goods_id>', methods=["GET", "POST"])
def full_goods_admin(goods_id):
    if not verify_curr_admin():
        return access_error()

    data = D.get_data(base_req=True, edit_goods_req=True)
    if not data:
        return server_error()
    api_response = goodsAPI.get(goods_id)
    if not api_response['success']:
        return error(message=api_response['message'])
    data.update(api_response['data'])

    t = api_response['data']['goods']['name']

    if request.method == "POST":
        form = get_request_data(files=True)
        if {'changeBtn', 'btnAddPhoto', 'delete_photo'} & set(form.keys()):
            api_response = goodsAPI.put(goods_id, request_data=form)
            if not api_response['success']:
                return server_error()
            data['menu_items'] = D.get_base_data()['menu_items']
            data['errors']['edit_goods'].update(api_response['errors'])
            api_response = goodsAPI.get(goods_id)
            if not api_response['success']:
                return server_error(message=api_response['message'])
            data.update(api_response['data'])

    return render('goods-admin.html', title=t, data=data)


def sign_in(page, t, data, ready_data=None):
    if get_authorization()['id']:
        return redirect('/lk')

    api_response = authorizationAPI.get(request_data=ready_data if ready_data else get_request_data())
    if api_response['success']:
        a = get_authorization(tmp_login=request.form['login'], tmp_password=request.form['password'], img=True)
        if page in ('sign-up.html', 'lk.html'):
            if verify_curr_admin(a):
                data = D.get_data(base_req=True, lk_admin_req=True, a=a)
                page = 'lk-admin.html'
            else:
                data = D.get_data(base_req=True, lk_req=True, a=a)
                page = 'lk.html'
        if not data:
            return error()
        if page == 'goods.html' and verify_curr_admin(a):
            data['errors'].update(D.get_edit_goods_data()['errors'])
            page = 'goods-admin.html'
        resp = make_response(render(page, a=a, title=t, data=data))
        resp.set_cookie('userID', str(a['id']))
        resp.set_cookie('userLogin', str(a['login']))
        resp.set_cookie('userPassword', str(a['password']))
    else:
        data['errors']['authorization'].update(api_response['errors'])
        data['errors']['authorization']['any'] = True
        data['last']['authorization']['login'] = request.form['login']
        data['last']['authorization']['password'] = request.form['password']
        resp = make_response(render(page, title=t, data=data))
    return resp


@app.route('/sign-out')
def sign_out():
    resp = make_response(redirect('/'))
    for cookie in ('userID', 'userLogin', 'userPassword'):
        resp.set_cookie(cookie, '', expires=0)
    return resp


@app.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    if get_authorization()['id']:
        return redirect('/lk')

    t = 'Регистрация'
    data = D.get_data(base_req=True, reg_req=True)
    if not data:
        return server_error()

    if request.method == "GET":
        return render('sign-up.html', t=t, data=data)

    elif request.method == "POST":
        form = get_request_data()
        if 'sign-in' in form:
            return sign_in('sign-up.html', t, data)

        api_response = authorizationAPI.post(request_data=form)
        if api_response['success']:
            return sign_in('lk.html', t='Успешно', data=data, ready_data={'id': api_response['success'],
                                                                          'login': form['login'],
                                                                          'password': form['password']})
        else:
            data['errors']['registration'].update(api_response['errors'])
            data['last']['registration'].update(form)
    return render('sign-up.html', t=t, data=data)


@app.route('/lk', methods=["GET", "POST"])
def lk():
    t = "Личный кабинет"
    if verify_curr_admin():
        return redirect('/lk-admin')
    elif verify_authorization():
        data = D.get_data(base_req=True, lk_req=True)
        if not data:
            return server_error()

        request_data = get_request_data(files=True)

        if request.method == 'POST':
            if 'changeUserInfoBtn' in request_data:
                response = userAPI.put(get_authorization()['id'], request_data=request_data)
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
            elif 'photo' in request_data:
                response = userAPI.put(get_authorization()['id'], request_data=request_data)
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
            elif 'deleteUserBtn' in request_data:
                resp = userAPI.delete(request_data['deleteUserBtn'])
                if resp['success']:
                    return sign_out()
            elif 'deleteOrderBtn' in request_data:
                resp = orderAPI.delete(request_data['deleteOrderBtn'])
                if not resp['success']:
                    data['errors']['edit_order'] = resp['message']
            elif 'cancelOrderBtn' in request_data:
                resp = orderAPI.put(request_data['cancelOrderBtn'], params={'status': 'cancel'})
                if not resp['success']:
                    data['errors']['edit_order'] = resp['message']
        return render("lk.html", title=t, data=data)
    return redirect('/')


@app.route('/lk-admin', methods=["GET", "POST"])
def lk_admin():
    t = "Личный кабинет (ADMIN)"
    if verify_curr_admin():
        data = D.get_data(base_req=True, lk_admin_req=True)
        if not data:
            return server_error()
        category = data['curr_category']

        if request.method == 'GET':
            return render("lk-admin.html", title=t, data=data)

        form = get_request_data()
        if request.method == 'POST':
            err = {'add_data': {},
                   'add_goods': {}}
            last = dict()
            if 'addGoodsBtn' in form:
                category = 'goods'
                resp = goodsAPI.post('new', request_data=form)
                if not resp['success']:
                    err['add_goods'] = resp['errors']
                    last['add_goods'] = form
                    category = 'addGoods'
            elif 'deleteGoodsBtn' in form:
                category = 'goods'
                resp = goodsAPI.delete(form['deleteGoodsBtn'])
                if not resp['success']:
                    err['add_data']['goods'] = resp['message']
            elif 'deleteOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.delete(form['deleteOrderBtn'])
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'cancelOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put(form['cancelOrderBtn'], params={'status': 'cancel'})
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'deliveredOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put(form['deliveredOrderBtn'], params={'status': 'delivered'})
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'doneOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put(form['doneOrderBtn'], params={'status': 'done'})
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'deleteUserBtn' in form:
                category = 'users'
                resp = userAPI.delete(form['deleteUserBtn'])
                if not resp['success']:
                    err['add_data']['users'] = resp['message']
            data = D.get_data(base_req=True, lk_admin_req=True)
            if not data:
                return error()
            if err:
                data['errors'].update(err)
            if last:
                data['last'].update(last)
            data['curr_category'] = category
        return render("lk-admin.html", title=t, data=data)
    elif verify_authorization():
        return redirect('/lk')
    return redirect('/')


@app.route('/basket', methods=["GET", "POST"])
def user_basket():
    t = "Корзина"
    if request.method == "POST":
        form = get_request_data()
        if 'editCountGoodsBtn' in form:
            basketAPI.put(form['editCountGoodsBtn'], params={'count': form['countGoods']})

        if 'deleteGoodsBtn' in form:
            api_response = basketAPI.delete(form['deleteGoodsBtn'])
            if not api_response['success']:
                logging.error("Basket delete goods error:\t{}".format(api_response['message']))

    data = D.get_data(base_req=True, basket_req=True)
    if 'basket_data' not in data:
        return access_error()
    return render("basket.html", title=t, data=data)


@app.route('/make-order', methods=["GET", "POST"])
def make_order():
    t = "Оформление заказа"
    data = D.get_data(base_req=True, order_req=True)
    if 'order_data' not in data:
        return access_error()

    if request.method == "POST":
        if 'finishBtn' in request.form:
            api_response = orderAPI.post('curr')
            if api_response['success']:
                data = D.get_base_data()
                data['message'] = "Заказ №{} успешно создан. " \
                                  "Ожидайте звонка для подтвержения.".format(api_response['order_id'])
                return render('success.html', title=t, data=data)
            else:
                data = D.get_data(base_req=True, order_req=True)
                if api_response['message'] == "Goods count error":
                    data['errors']['order_goods'] = api_response['goods']
                data['errors']['order'] = api_response['message']

    return render("order.html", title=t, data=data)


@app.route('/contacts', methods=["GET", "POST"])
def show_contacts():
    t = "Контакты"
    data = D.get_base_data()
    if request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('contacts.html', t, data)
    return render("contacts.html", title=t, data=data)


@app.route('/help', methods=["GET", "POST"])
def show_help():
    t = "Помощь покупателю"
    data = D.get_base_data()
    if request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('help.html', t, data)
    return render("help.html", title=t, data=data)


def error(err=520, message='Что-то пошло не так :('):
    data = D.get_base_data(anyway=True)
    data.update({'message': message, 'type': err})
    return render('error.html', data=data)


@app.errorhandler(401)
def access_error(err=None, message=''):
    return error(401, 'Отказано в доступе :(\n{}'.format(message))


@app.errorhandler(404)
def not_found(err=None, message=''):
    return error(404, 'Страница не найдена :(\n{}'.format(message))


@app.errorhandler(500)
def server_error(err=None, message=''):
    return error(500, 'Ошибка сервера :(\n{}'.format(message))


@app.route('/index')
def index():
    return redirect('/')


def render(template, a=None, **kwargs):
    authorization = a if a else get_authorization(img=True)
    if (not a) and (not verify_authorization(admin=True)):
        sign_out()
        return render_template(template, authorization=get_authorization(), **kwargs)
    return render_template(template, authorization=authorization, **kwargs)


def make_success(state=True, message='Ok', **kwargs):
    data = {'success': state if state else False}
    if message == 'Ok':
        message = 'Ok' if state else 'Unknown Error'
    data['message'] = message
    data.update(kwargs)
    return data


def get_request_data(files=False):
    form = dict(request.form)
    if files:
        form.update(dict(request.files))
    for i in form:
        if type(form[i]) is list and i != 'add_photo':
            form[i] = form[i][-1]
    return form


# данные админа
ADMIN_ID = -1
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"

D = DataTemplate()
db.create_all()

# Все API
userAPI = UserAPI()
goodsAPI = GoodsAPI()
searchAPI = SearchAPI()
basketAPI = BasketAPI()
orderAPI = OrderAPI()
authorizationAPI = AuthorizationAPI()

# подключение API
api.add_resource(AuthorizationAPI, '/api/authorization/<path:r>')
api.add_resource(UserAPI, '/api/users/<path:r>')
api.add_resource(GoodsAPI, '/api/goods/<path:r>')
api.add_resource(BasketAPI, '/api/basket/<path:r>')
api.add_resource(OrderAPI, '/api/orders/<path:r>')
api.add_resource(SearchAPI, '/api/search/<path:r>')

if __name__ == '__main__':
    # http://neo120.pythonanywhere.com/
    app.run(port=8080, host='127.0.0.1')
