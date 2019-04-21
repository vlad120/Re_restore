from flask import Flask, render_template, redirect, request, make_response
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from os import remove, listdir, makedirs, rmdir, path, rename
from shutil import copyfile
from copy import deepcopy


app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'myOwn_secretKey_nobodyCan_hackIt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///all_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

NO_GOODS_PHOTO = '/static/goods/NoPhoto.jpg'
NO_PROFILE_PHOTO = '/static/profiles/NoPhoto.jpg'


def get_authorization(tmp_id=None, tmp_login=None, tmp_password=None,
                      img=False, params=None):
    if params and type(params) == dict and 'authorization' in params:
        if params['authorization']:
            try:
                p = params['authorization'].split(';')
                tmp_login, tmp_password = p[0], p[1]
                tmp_id = UserModel.query.filter_by(login=tmp_login).first().id
            except:
                tmp_id, tmp_login, tmp_password = None, None, None

    a = {'id': tmp_id if tmp_id else request.cookies.get('userID'),
         'login': tmp_login if tmp_login else request.cookies.get('userLogin'),
         'password': tmp_password if tmp_password else request.cookies.get('userPassword')}
    if img and a['id']:
        user = UserModel.query.filter_by(id=a['id']).first()
        if user:
            a.update(user.to_dict(photo_req=True))
        else:
            a['photo'] = '/static/profiles/NoPhoto.jpg'
    return a


def verify_curr_admin(a=None):
    a = a if a else get_authorization()
    if a and a['id'] and int(a['id']) == ADMIN_ID and a['login'] == ADMIN_LOGIN and \
            a['password'] == ADMIN_PASSWORD:
        return True
    return False


def verify_authorization(admin=False, a=None):
    if admin and verify_curr_admin():
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
    name = "_".join(goods.name[:10].split())
    category = (category if category else goods.category).strip(' /')
    return 'static/goods/{}/{}'.format(category, name) + ('/' if sl else '')


def get_api_params(r):
    params = dict()
    if len(r) > 1:
        try:
            for i in (p.split('=') for p in r[1].split('&')):
                params[i[0]] = i[1]
        except:
            pass
    return params


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
                price_req=True, count_req=False, category_req=True,
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
            d['full_link'] = '{}/{}/{}'.format(HOME, self.category.strip(' /'), self.id)
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
            d['link'] = HOME + '/' + self.name
        return d


class OrderModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    total = db.Column(db.Float, nullable=False)
    goods = db.Column(db.JSON, nullable=False)
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
            d['goods'] = dict(self.goods)['goods']
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
    basket = db.Column(db.JSON, default={'basket': []})

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
    def get_data(self, tmp_a=None, base_req=False, main_req=False,
                 lk_req=False, lk_admin_req=False, reg_req=False,
                 edit_goods_req=False, basket_req=False, order_req=False):
        data = dict()
        try:
            if base_req:
                data.update(self.get_base_data())
            if main_req:
                data.update(self.get_main_data())
            if lk_req:
                t = self.get_lk_data(tmp_a)
                data['user'] = t['user']
                data['errors'].update(t['errors'])
            if lk_admin_req:
                t = self.get_lk_admin_data(tmp_a)
                data['errors'].update(t.pop('errors'))
                data.update(t)
            if reg_req:
                t = self.get_registration_data()
                data['last'].update(t['last'])
                data['errors'].update(t['errors'])
            if edit_goods_req:
                data['errors'].update(self.get_edit_goods_data()['errors'])
            if basket_req:
                t = self.get_basket_data(tmp_a)
                data['basket_data'] = t['basket_data']
                data['errors']['basket'] = t['errors']['basket']
            if order_req:
                data.update(self.get_order_data(tmp_a))
            return data
        except Exception as e:
            print("Data template get Error:\t", e)
            return None

    def get_base_data(self, anyway=False):
        try:
            api_response = basketAPI.get(['curr'])
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
            print("Get base data template Error: ", e)
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

    def get_main_data(self):
        try:
            interesting_goods = '10'
            api_response = goodsAPI.get(['random', 'n=' + interesting_goods])
            if api_response['success']:
                goods = api_response['goods']
                return {'slides': ['static/main_banners/{}.png'.format(i + 1) for i in range(4)],
                        'len_slides': 4,
                        'goods': goods
                        }
        except Exception as e:
            print("Get main data template Error: ", e)

    def get_lk_data(self, tmp_a=None):
        try:
            user_id = (tmp_a if tmp_a else get_authorization())['id']
            api_response = userAPI.get([user_id], a=tmp_a)
            if api_response['success']:
                return {'user': api_response['user'],
                        'errors': {'change_profile_info': {'name': None,
                                                           'surname': None,
                                                           'email': None,
                                                           'check_password': None,
                                                           'new_password': None,
                                                           'photo': None}},
                        }
        except Exception as e:
            print("Get lk data template Error: ", e)

    def get_lk_admin_data(self, a=None):
        try:
            a = a if a else get_authorization()
            goods_response = goodsAPI.get(['all'], a)
            orders_response = orderAPI.get(['all'], a)
            users_response = userAPI.get(['all'], a)
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
            print("Get lk-admin data template Error: ", e)

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
            print("Get registration data template Error: ", e)

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
                api_response = basketAPI.get(['curr'])
                basket = [[(int(i), int(g[i])) for i in g][0] for g in api_response['basket']]
                goods = [goodsAPI.get([g[0]])['data']['goods'] for g in basket]
                for i in range(len(goods)):
                    goods[i]['count'] = basket[i][1]
                if api_response['success']:
                    return {'basket_data': {'goods': goods,
                                            'total': sum(g['price'] * g['count'] for g in goods)
                                            },
                            'errors': {'basket': {'order': None}}
                            }
            except Exception as e:
                print("Get basket data template Error: ", e)
                return {}

    def get_order_data(self, a=None):
        return {}


class Authorization(Resource):
    # Авторизация
    def get(self, request_data=None):
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
            print("AuthorizationAPI Error:\t", e)
            errors['other'] = "Ошибка сервера."
        return make_success(False, errors=errors)

    # Регистрация
    def post(self, request_data=None):
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
            print("RegistrationAPI Error:\t", e)
            errors['other'] = "Ошибка сервера."
            return make_success(False, message="Server error", errors=errors)


class User(Resource):
    def get(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization()

        if type(r[0]) is int or str(r[0]).isdigit():
            user_id = int(r[0])
            user = UserModel.query.filter_by(id=user_id).first()
            # проверка на существование
            if not user:
                return make_success(False, message="User {} doesn't exist".format(user_id))
            # проверка на собственника учетной записи / админа
            if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                return make_success(False, message="Access Error")
            return make_success(user=user.to_dict(all_req=True))

        if str(r[0]).lower() == 'all':
            if not verify_curr_admin(a):
                return make_success(False, message='Access Error')
            try:
                return make_success(users=[i.to_dict(name_req=True, surname_req=True,
                                                     email_req=True, login_req=True) for i in
                                           UserModel.query.all()])
            except Exception as e:
                print('UserAPI Error (get all): ', e)
                return make_success(False, message='Server Error')
        return make_success(False, message='Bad request')

    def put(self, r, a=None, request_data=None):
        params = get_api_params(r)
        a = a if a else get_authorization()

        if type(r[0]) is int or str(r[0]).isdigit():
            errors = {'name': None,
                      'surname': None,
                      'email': None,
                      'check_password': None,
                      'new_password': None,
                      'photo': None}
            try:
                user_id = int(r[0])
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

                if 'photo' in args and args['photo']:
                    photo_name = None
                    try:
                        ext = args['photo'].filename.split('.')[-1]
                        if ext.lower() in ['png', 'jpg', 'jpeg']:
                            photo_name = '{}.{}'.format(user.id, 'png')
                            args['photo'].save('static/profiles/' + photo_name)
                            user.photo = photo_name
                            db.session.commit()
                        else:
                            raise TypeError
                    except Exception as e:
                        print("Save photo (change user info) Error:\t", e)
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

        return make_success(False, 'Bad request')

    def delete(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization()

        if type(r[0]) is int or str(r[0]).isdigit():
            user_id = int(r[0])
            # проверка на собственника учетной записи / админа
            if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                return make_success(False, message="Access Error")
            try:
                user = UserModel.query.filter_by(id=user_id).first()
                if user:
                    # удаляем все заказы пользователя
                    for order in OrderModel.query.filter_by(user_id=user_id).all():
                        db.session.delete(order)
                    db.session.delete(user)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="User {} doesn't exist".format(user_id))
            except Exception as e:
                print("User delete Error:\t", e)
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


class Goods(Resource):
    def get(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        # полная информация об одном товаре
        if type(r[0]) is int or str(r[0]).isdigit():
            goods_id = int(r[0])
            try:
                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if not goods:
                    return make_success(False, message="Goods {} doesn't exist".format(goods_id))
                return make_success(data={'goods': goods.to_dict(description_req=True,
                                                                 short_description_req=True,
                                                                 photos_req=True,
                                                                 count_req=True,
                                                                 full_category_req=True,
                                                                 full_link_req=True)})
            except Exception as e:
                print("GoodsAPI Error (get {}): ".format(goods_id), e)
                return make_success(False, message='Server Error')

        # краткая информация обо всех товарах для админа
        if str(r[0]).lower() == 'all':
            if verify_curr_admin(a):
                try:
                    return make_success(goods=[i.to_dict(full_link_req=True, short_description_req=True)
                                               for i in reversed(GoodsModel.query.all())])
                except Exception as e:
                    print("GoodsAPI Error (get all): ", e)
                    return make_success(False, message='Server Error')
            return make_success(False, message='Access Error')

        # 1 или несколько рандомных товаров
        if str(r[0]).lower() == 'random':
            try:
                n = int(params['n']) if 'n' in params else 1
                # множество перемешанных товаров (которые есть в наличии)
                goods = set(filter(lambda g: g.count > 0, (i for i in GoodsModel.query.all())))
                # обрезка до нужного количества и
                # преобразование каждого товара в словарь
                goods = list(g.to_dict(photo_req=True, full_link_req=True,
                                       card_description_req=True) for g in list(goods)[:n])
                return make_success(goods=goods)
            except Exception as e:
                print("GoodsAPI Error (get random): ", e)
                return make_success(False, message='Server Error')

        # все товары данной категории
        category = CategoryModel.query.filter_by(name=str(r[0]).lower()).first()
        if category:
            try:
                goods = GoodsModel.query.all()
                if 'sort' in params:
                    if params['sort'] == 'NEW':
                        goods.sort(key=lambda g: g.id, reverse=True)
                    elif params['sort'] == 'CHE':
                        goods.sort(key=lambda g: int(g.price))
                    elif params['sort'] == 'EXP':
                        goods.sort(key=lambda g: int(g.price), reverse=True)
                return make_success(goods=[i.to_dict(full_link_req=True,
                                                     card_description_req=True,
                                                     photo_req=True) for i in goods],
                                    category=category.to_dict())
            except Exception as e:
                print("GoodsAPI Error (get category {}): ".format(r[0]), e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def post(self, r, a=None, request_data=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if str(r[0]).lower() == 'new':
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
                    if errors['name']:
                        errors['name'] += " Название не может содержать символ '/'"
                    else:
                        errors['name'] = "Название не может содержать символ '/'"

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
                print("GoodsAPI Error (add goods): ", e)
                return make_success(False, message="Server error", errors=errors)

        return make_success(False, message='Bad request')

    def put(self, r, a=None, request_data=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if type(r[0]) is int or str(r[0]).isdigit():
            errors = D.get_edit_goods_data()['errors']['edit_goods']
            try:
                goods_id = int(r[0])
                parser = reqparse.RequestParser()
                for arg in errors.keys():
                    parser.add_argument(arg)
                args = parser.parse_args()
                if request_data:
                    args.update(request_data)

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
                            errors['name'] = "Название должно быть не более 80 символов."
                        elif '/' in args['name']:
                            errors['name'] = "Название не может содержать символ '/'"
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
                if args['category'] and args['category'] != goods.category:
                    try:
                        args['category'] = args['category'].strip('/')
                        if len(args['category']) > 150:
                            errors['category'] = "Категория должна быть не более 150 символов."
                        else:
                            old_category = CategoryModel.query.filter_by(name=goods.category).first()
                            rus_category = old_category.rus_name
                            if args['rus_category'] != rus_category:
                                if len(args['rus_category']) > 150:
                                    errors['rus_category'] = "Категория должна быть не более 150 символов."
                                else:
                                    rus_category = args['rus_category']
                            new_category = CategoryModel(name=args['category'], rus_name=rus_category)

                            try:
                                new_folder = get_folder(goods, category=new_category.name, sl=False)
                                old_folder = get_folder(goods, category=old_category.name, sl=False)
                                if not path.exists(new_folder):
                                    makedirs(new_folder)
                                if path.exists(old_folder):
                                    for item in listdir(old_folder):
                                        copyfile(old_folder + '/' + item, new_folder + '/' + item)
                                        remove(old_folder + '/' + item)
                                    rmdir(old_folder)
                                    old_category_folder = "/".join(old_folder.split('/')[:-1])
                                    if not listdir(old_category_folder):
                                        rmdir(old_category_folder)
                            except Exception as e:
                                print("GoodsAPI Error (move goods folder): ", e)

                            folder = get_folder(goods, category=new_category.name, sl=False)
                            if not path.exists(folder):
                                makedirs(folder)
                                print("GoodsAPI Error (unknown, move folder) - done!")

                            if len(GoodsModel.query.filter_by(category=old_category.name).all()) == 1:
                                db.session.delete(old_category)
                                db.session.commit()
                            db.session.add(new_category)
                            db.session.commit()
                            goods.category = args['category']
                            db.session.commit()
                    except Exception as e:
                        print("GoodsAPI Error (set directory while edit info): ", e)
                        errors['category'] = unknown_err

                elif args['rus_category']:
                    try:
                        category = CategoryModel.query.filter_by(name=goods.category).first()
                        if args['rus_category'] != category.rus_name:
                            category.rus_name = args['rus_category']
                            db.session.commit()
                    except:
                        errors['rus_category'] = "Некорректные данные"

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
                        print("GoodsAPI Error (edit short description while edit info): ", e)
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
                        print("GoodsAPI Error (edit description while edit info): ", e)
                        errors['short_description'] = unknown_err

                # удаление фото
                if args['delete_photo']:
                    try:
                        if args['delete_photo'].strip('/') != NO_GOODS_PHOTO.strip('/'):
                            remove(args['delete_photo'])
                            photos = goods.photos.split(';')
                            photo = args['delete_photo'].split('/')[-1]
                            for i in range(photos.count(photo)):
                                photos.remove(photo)
                            goods.photos = ";".join(photos) if photos else NO_GOODS_PHOTO
                            db.session.commit()
                    except Exception as e:
                        print("GoodsAPI Error (delete photo while edit info): ", e)
                        errors['delete_photo'] = "Ошибка сервера при удалении фото."

                # добавление фотографий
                if args['add_photo'] and any(filter(lambda p: bool(p), args['add_photo'])):
                    try:
                        if type(args['add_photo']) is not list:
                            args['add_photo'] = [args['add_photo']]
                        goods_photos = goods.photos.split(';')
                        for i in range(len(args['add_photo'])):
                            photo = args['add_photo'][i]
                            if photo.filename in goods_photos:
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
                                print("GoodsAPI Error (edit info, save photo): ", e)
                                if photo:
                                    url = '{}/{}'.format(get_folder(goods, sl=False), photo.filename)
                                    if path.exists(url):
                                        remove(url)
                                errors['add_photo'] = "Ошибка при загрузке некоторых фото."
                    except Exception as e:
                        print("GoodsAPI Error (load photo while edit info): ", e)
                        errors['add_photo'] = "Ошибка при загрузке фото."

                db.session.commit()
                return make_success(errors=errors)
            except Exception as e:
                print("Change goods info Error:\t", e)
                return make_success(False, 'Server error')

        return make_success(False, 'Bad request')

    def delete(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if type(r[0]) is int or str(r[0]).isdigit():
            # проверка на админа
            if not verify_curr_admin(a):
                return make_success(False, message="Access Error")

            try:
                goods_id = int(r[0])
                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if goods:
                    db.session.delete(goods)
                    db.session.commit()
                    folder = get_folder(goods, sl=False)
                    if path.exists(folder):
                        for item in listdir(folder):
                            remove('{}/{}'.format(folder, item))
                        rmdir(folder)
                    return make_success()
                return make_success(False, message="Goods doesn't exist")
            except Exception as e:
                print("Goods delete Error:\t", e)
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


class Bassket(Resource):
    def get(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if r[0] == 'curr':
            try:
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    return make_success(basket=user.basket['basket'])
                return make_success(False, "Authorization error")
            except Exception as e:
                print("BassketAPI Error (get): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def post(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if type(r[0]) is int or str(r[0]).isdigit():
            try:
                if not GoodsModel.query.filter_by(id=r[0]).first():
                    return make_success(False, message="Goods doesn't exist")
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    if r[0] in [[k for k in g][0] for g in user.basket['basket']]:
                        return make_success(False, message="Goods has already added")
                    basket = user.basket['basket'][:]
                    basket.append({str(r[0]): (int(params['count']) if 'count' in params else 1)})
                    user.basket = {"basket": basket}
                    db.session.commit()
                    return make_success()
                return make_success(False, "Authorization error")
            except Exception as e:
                print("BassketAPI Error (add): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def put(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if type(r[0]) is int or str(r[0]).isdigit():
            try:
                if not GoodsModel.query.filter_by(id=r[0]).first():
                    return make_success(False, message="Goods doesn't exist")
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    names = [[k for k in g][0] for g in user.basket['basket']]
                    if r[0] not in names:
                        return make_success(False, message="Goods is not in basket")
                    if 'count' in params and params['count'].isdigit() and int(params['count']) > 0:
                        basket = deepcopy(user.basket['basket'])
                        basket[names.index(r[0])][r[0]] = int(params['count'])
                        user.basket = {'basket': basket}
                    else:
                        return make_success(False, "Count error")
                    db.session.commit()
                    return make_success()
                return make_success(False, "Authorization error")
            except Exception as e:
                print("BassketAPI Error (edit): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def delete(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization(params=params)

        if type(r[0]) is int or str(r[0]).isdigit():
            try:
                if not GoodsModel.query.filter_by(id=r[0]).first():
                    return make_success(False, message="Goods doesn't exist")
                if a:
                    user = UserModel.query.filter_by(id=a['id']).first()
                    if not user:
                        return make_success(False, message="User not found")
                    names = [[k for k in g][0] for g in user.basket['basket']]
                    if r[0] not in names:
                        return make_success(False, message="Goods is not in basket")
                    basket = user.basket['basket'][:]
                    del basket[names.index(r[0])]
                    user.basket = {'basket': basket}
                    db.session.commit()
                    return make_success()
                return make_success(False, "Authorization error")
            except Exception as e:
                print("BassketAPI Error (delete): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')


class Order(Resource):
    def get(self, r, a=None):
        params = get_api_params(r)

        if str(r[0]).lower() == 'all':
            if not verify_curr_admin(a):
                return make_success(False, message='Access Error')
            try:
                return make_success(orders=[i.to_dict() for i in OrderModel.query.all()])
            except Exception as e:
                print("OrderAPI Error (): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def delete(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization()

        if type(r[0]) is int or str(r[0]).isdigit():
            try:
                order_id = int(r[0])
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
                print("Order delete Error:\t", e)
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')

    def put(self, r, a=None):
        params = get_api_params(r)
        a = a if a else get_authorization()

        if type(r[0]) is int or str(r[0]).isdigit():
            try:
                if 'status' in params:
                    order_id = int(r[0])
                    order = OrderModel.query.filter_by(id=order_id).first()
                    if order:
                        # проверка на админа
                        if not verify_curr_admin(a):
                            return make_success(False, message="Access Error")
                        order.status = params['status']
                        db.session.commit()
                        return make_success()
                    return make_success(False, message="Order doesn't exist")
            except Exception as e:
                print("Order put Error:\t", e)
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


@app.route('/re_restore', methods=["GET", "POST"])
def re_restore():
    t = 'Добро пожаловать в Re_restore!'
    data = D.get_data(base_req=True, main_req=True)

    if request.method == "GET":
        return render('index.html', title=t, data=data)

    elif request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('index.html', t, data)

        if 'addToBasket' in request.form:
            api_response = basketAPI.post([request.form['addToBasketGoodsID']])
            if not api_response['success']:
                print("Add to basket error: ", api_response['message'])
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']
            return render('index.html', title=t, data=data)


@app.route('/re_restore/<string:category>', methods=["GET", "POST"])
def goods_category(category):
    data = D.get_base_data()
    data['sorting'] = request.cookies.get('sorting')
    if not data['sorting']:
        data['sorting'] = 'NEW'
    api_response = goodsAPI.get([category, 'sort=' + data['sorting']])
    if api_response['success']:
        data['goods'] = api_response['goods']
        data['full_category'] = api_response['category']

    t = api_response['category']['rus_name']

    if request.method == "GET":
        return render('goods-category.html', title=t, data=data)

    form = get_request_data()
    if request.method == "POST":
        if 'sign-in' in form:
            return sign_in('goods-category.html', 'Вход', data)

        if 'addToBasket' in form:
            api_response = basketAPI.post([form['addToBasketGoodsID']])
            if not api_response['success']:
                print("Add to basket error: ", api_response['message'])
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']
            return render('goods-category.html', title=t, data=data)

        if 'sorting' in form:
            data['sorting'] = form['sorting']
            api_response = goodsAPI.get([category, 'sort=' + data['sorting']])
            if api_response['success']:
                data['goods'] = api_response['goods']
            resp = make_response(render('goods-category.html', title=t, data=data))
            resp.set_cookie('sorting', form['sorting'])
            return resp


@app.route('/re_restore/<string:category>/<int:goods_id>', methods=["GET", "POST"])
def full_goods(category, goods_id):
    curr_admin = verify_curr_admin()

    data = D.get_data(base_req=True, edit_goods_req=True if curr_admin else False)
    if not data:
        return server_error()

    api_response = goodsAPI.get([goods_id])
    if not api_response['success']:
        return error(message=api_response['message'])
    data.update(api_response['data'])

    t = api_response['data']['goods']['name']

    if request.method == "GET":
        if curr_admin:
            return render('goods-admin.html', title=t, data=data)
        return render('goods.html', title=t, data=data)
    if request.method == "POST":
        form = get_request_data(files=True)
        if 'sign-in' in form:
            return sign_in('goods.html', t, data)

        if 'addToBasket' in form:
            api_response = basketAPI.post([form['addToBasketGoodsID']])
            if not api_response['success']:
                print("Add to basket error: ", api_response['message'])
            else:
                new_data = D.get_base_data()
                data['len_basket'] = new_data['len_basket']
                data['basket'] = new_data['basket']
            return render('goods.html', title=t, data=data)

        if curr_admin:
            if {'changeBtn', 'btnAddPhoto', 'delete_photo'} & set(form.keys()):
                api_response = goodsAPI.put([goods_id], request_data=form)
                if api_response['success']:
                    data['errors']['edit_goods'].update(api_response['errors'])

                    api_response = goodsAPI.get([goods_id])
                    if not api_response['success']:
                        return error(message=api_response['message'])
                    data.update(api_response['data'])

                    return render('goods-admin.html', title=t, data=data)
                return server_error()


def sign_in(page, t, data, ready_data=None):
    if get_authorization()['id']:
        return redirect('/lk')

    response = authorizationAPI.get(request_data=ready_data if ready_data else get_request_data())
    if response['success']:
        a = get_authorization(response['success'], request.form['login'], request.form['password'], img=True)
        if page in ('sign-up.html', 'lk.html'):
            if verify_curr_admin(a):
                data = D.get_data(base_req=True, lk_admin_req=True, tmp_a=a)
                page = 'lk-admin.html'
            else:
                data = D.get_data(base_req=True, lk_req=True, tmp_a=a)
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
    if not data:
        return server_error()

    if request.method == "GET":
        return render('sign-up.html', t=t, data=data)

    elif request.method == "POST":
        form = get_request_data()
        if 'sign-in' in form:
            return sign_in('sign-up.html', t, data)

        response = authorizationAPI.post(request_data=form)
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
        if not data:
            return server_error()

        request_data = get_request_data(files=True)

        if request.method == 'POST':
            if 'changeUserInfoBtn' in request_data:
                response = userAPI.put([get_authorization()['id']], request_data=request_data)
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
            if 'photo' in request_data:
                response = userAPI.put([get_authorization()['id']], request_data=request_data)
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
            if 'deleteUserBtn' in request_data:
                resp = userAPI.delete([request_data['deleteUserBtn']])
                if resp['success']:
                    return sign_out()
        return render("lk.html", title=t, data=data)
    return redirect(HOME)


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
                response = goodsAPI.post(['new'], request_data=form)
                if not response['success']:
                    err['add_goods'] = response['errors']
                    last['add_goods'] = form
                    category = 'addGoods'
            elif 'deleteGoodsBtn' in form:
                category = 'goods'
                resp = goodsAPI.delete([form['deleteGoodsBtn']])
                if not resp['success']:
                    err['add_data']['goods'] = resp['message']
            elif 'deleteOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.delete([form['deleteOrderBtn']])
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'cancelOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put([form['cancelOrderBtn'], 'status=cancel'])
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'doneOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put([form['doneOrderBtn'], 'status=done'])
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'deleteUserBtn' in form:
                category = 'users'
                resp = userAPI.delete([form['deleteUserBtn']])
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
    return redirect(HOME)


@app.route('/basket', methods=["GET", "POST"])
def user_basket():
    t = "Корзина"
    if request.method == "POST":
        form = get_request_data()
        if 'editCountGoodsBtn' in form:
            api_response = basketAPI.put([form['editCountGoodsBtn'], "count=" + form['countGoods']])
            if not api_response['success']:
                print("Basket edit count goods error: ", api_response['message'])

        if 'deleteGoodsBtn' in form:
            api_response = basketAPI.delete([form['deleteGoodsBtn']])
            if not api_response['success']:
                print("Basket delete goods error: ", api_response['message'])

    data = D.get_data(base_req=True, basket_req=True)
    if 'basket_data' not in data:
        return access_error()
    return render("basket.html", title=t, data=data)


@app.route('/make-order', methods=["GET", "POST"])
def make_order():
    t = "Оформление заказа"
    data = D.get_data(base_req=True, order_req=True)
    return render("order.html", title=t, data=data)


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


@app.route('/')
@app.route('/index')
def index():
    return redirect(HOME)


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


HOME = '/re_restore'
HOST = '127.0.0.1'
PORT = 8080

# данные админа
ADMIN_ID = -1
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"

# Все API
userAPI = User()
goodsAPI = Goods()
basketAPI = Bassket()
orderAPI = Order()
authorizationAPI = Authorization()

D = DataTemplate()

if __name__ == '__main__':
    db.create_all()

    api.add_resource(Authorization, '/authorization')
    api.add_resource(User, '/users/<path:r>')
    api.add_resource(Goods, '/goods/<path:r>')
    api.add_resource(Bassket, '/basket/<path:r>')
    api.add_resource(Order, '/order/<path:r>')

    app.run(port=PORT, host=HOST)
