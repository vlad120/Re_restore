from flask import Flask, render_template, redirect, request, make_response
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from os import remove


app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'myOwn_secretKey_nobodyCan_hackIt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///all_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class GoodsModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(15000), nullable=False)
    short_description = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(150), nullable=False)
    photos = db.Column(db.String(500), default='/static/goods/NoPhoto.jpg')

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
            d['full_link'] = '{}/{}/{}'.format(HOME, self.category.strip('/'), self.id)
        if photo_req:
            d['photo'] = self.photos.split(';')[0].strip()
        if photos_req:
            d['photos'] = [photo.strip() for photo in self.photos.split(';')]
            d['len_photos'] = len(self.photos.split(';'))
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
            d['photo'] = 'static/profiles/' + self.photo
        return d


class DataTemplate:
    def get_data(self, tmp_a=None, base_req=False, main_req=False,
                 lk_req=False, lk_admin_req=False, reg_req=False):
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
            return data
        except Exception as e:
            print("Data template get Error:\t", e)
            return

    def get_base_data(self):
        try:
            return {'menu_items': [c.to_dict() for c in CategoryModel.query.all()],
                    'basket': get_basket(),
                    'errors': {'authorization': {'password': None,
                                                 'login': None,
                                                 'other': None,
                                                 'any': False}},
                    'last': {'authorization': {'password': '',
                                               'login': ''}}
                    }
        except Exception as e:
            print("Get base data template Error: ", e)

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
            response = userAPI.get([user_id], a=tmp_a)
            if response['success']:
                return {'user': response['user'],
                        'errors': {'change_profile_info': {'name': None,
                                                           'surname': None,
                                                           'email': None,
                                                           'check_password': None,
                                                           'new_password': None,
                                                           'photo': None}},
                        }
        except Exception as e:
            print("Get lk data template Error: ", e)

    def get_lk_admin_data(self, tmp_a=None):
        try:
            goods_response = goodsAPI.get(['all'], tmp_a)
            orders_response = orderAPI.get(['all'], tmp_a)
            users_response = userAPI.get(['all'], tmp_a)
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


def get_authorization(tmp_id=None, tmp_login=None, tmp_password=None, img=False):
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


def get_basket():
    return []


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
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
            user_id = int(r[0])
            user = UserModel.query.filter_by(id=user_id).first()
            # проверка на существование
            if not user:
                return make_success(False, message="User {} doesn't exist".format(user_id))
            # проверка на собственника учетной записи / админа
            a = a if a else get_authorization()
            if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                return make_success(False, message="Access Error")
            return make_success(user=user.to_dict(all_req=True))

        if r[0].lower() == 'all':
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
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
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
                a = a if a else get_authorization()
                if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
                    return make_success(False, message="Access Error")

                if 'photo' in args and args['photo']:
                    photo_name = None
                    try:
                        ext = args['photo'][0].filename.split('.')[-1]
                        if ext.lower() in ['png', 'jpg', 'jpeg']:
                            photo_name = '{}.{}'.format(user.id, 'png')
                            args['photo'][0].save('static/profiles/' + photo_name)
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
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
            user_id = int(r[0])
            # проверка на собственника учетной записи / админа
            a = a if a else get_authorization()
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
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        # полная информация об одном товаре
        if type(r[0]) is int or r[0].isdigit():
            goods_id = int(r[0])
            try:
                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if not goods:
                    return make_success(False, message="Goods {} doesn't exist".format(goods_id))
                return make_success(data={'goods': goods.to_dict(description_req=True,
                                                                 short_description_req=True,
                                                                 photos_req=True,
                                                                 count_req=True,
                                                                 full_category_req=True)})
            except Exception as e:
                print("GoodsAPI Error (get {}): ".format(goods_id), e)
                return make_success(False, message='Server Error')

        # краткая информация обо всех товарах для админа
        if r[0].lower() == 'all':
            if verify_curr_admin(a):
                try:
                    return make_success(goods=[i.to_dict(full_link_req=True, short_description_req=True)
                                               for i in GoodsModel.query.all()])
                except Exception as e:
                    print("GoodsAPI Error (get all): ", e)
                    return make_success(False, message='Server Error')
            return make_success(False, message='Access Error')

        # 1 или несколько рандомных товаров
        if r[0].lower() == 'random':
            try:
                n = int(params['n']) if 'n' in params else 1
                # множество товаров (которые есть в наличии)
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
        category = CategoryModel.query.filter_by(name=r[0].lower()).first()
        if category:
            try:
                return make_success(goods=[i.to_dict(full_link_req=True,
                                                     card_description_req=True,
                                                     photo_req=True)
                                           for i in GoodsModel.query.all()
                                           ],
                                    category=category.to_dict())
            except Exception as e:
                print("GoodsAPI Error (get category {}): ".format(r[0]), e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def post(self, r, a=None, request_data=None):
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if r[0].lower() == 'new':
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

                args['category'].strip('/')

                # длина полей (для базы данных)
                if len(args['name']) > 80:
                    errors['name'] = "Название должно быть не более 80 символов."
                if len(args['description']) > 2000:
                    errors['description'] = "Описание должно быть не более 2000 символов."
                if len(args['short_description']) > 120:
                    errors['short_description'] = "Краткое описание должно быть не более 120 символов."
                if len(args['category']) > 150:
                    errors['category'] = "Категория не должна превышать 150 символов."
                if len(args['rus_category']) > 150:
                    errors['rus_category'] = "Категория не должна превышать 150 символов."

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

    def put(self, r, a=None):
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass
        # photos = []
        # if args['photos']:
        #     for i in range(len(args['photos'])):
        #         photo_name = None
        #         try:
        #             ext = args['photos'][i].filename.split('.')[-1]
        #             if ext.lower() in ['png', 'jpg', 'jpeg']:
        #                 photo_name = '{}.{}'.format(i, 'png')
        #                 args['photos'][i].save('static/goods/{}/{}/{}'.format(args['category'],
        #                                                                       args['name'],
        #                                                                       photo_name))
        #                 photos.append(photo_name)
        #             else:
        #                 raise TypeError
        #         except Exception as e:
        #             print("Save photos (add goods) Error:\t", e)
        #             if photo_name:
        #                 remove(photo_name)
        #                 errors['photos'] = "Ошибка при загрузке фото."
        # args['photos'] = ";".join(photos)
        return make_success()

    def delete(self, r, a=None):
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
            # проверка на админа
            a = a if a else get_authorization()
            if not verify_curr_admin(a):
                return make_success(False, message="Access Error")

            try:
                goods_id = int(r[0])
                goods = GoodsModel.query.filter_by(id=goods_id).first()
                if goods:
                    db.session.delete(goods)
                    db.session.commit()
                    return make_success()
                return make_success(False, message="Goods doesn't exist")
            except Exception as e:
                print("Goods delete Error:\t", e)
                return make_success(False, message="Server Error")

        return make_success(False, message='Bad request')


class Order(Resource):
    def get(self, r, a=None):
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if r[0].lower() == 'all':
            if not verify_curr_admin(a):
                return make_success(False, message='Access Error')
            try:
                return make_success(orders=[i.to_dict() for i in OrderModel.query.all()])
            except Exception as e:
                print("OrderAPI Error (): ", e)
                return make_success(False, message='Server Error')

        return make_success(False, message='Bad request')

    def delete(self, r, a=None):
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
            try:
                order_id = int(r[0])
                order = OrderModel.query.filter_by(id=order_id).first()
                if order:
                    # проверка на собственника учетной записи / админа
                    a = a if a else get_authorization()
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
        params = dict()
        if len(r) > 2:
            return make_success(False, message='Bad request')
        if len(r) == 2:
            try:
                for i in (p.split('=') for p in r[1].split('&')):
                    params[i[0]] = i[1]
            except:
                pass

        if type(r[0]) is int or r[0].isdigit():
            try:
                if 'status' in params:
                    order_id = int(r[0])
                    order = OrderModel.query.filter_by(id=order_id).first()
                    if order:
                        # проверка на админа
                        a = a if a else get_authorization()
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


@app.route('/re_restore/<string:category>')
def goods_category(category):
    api_response = goodsAPI.get([category])
    if api_response['success']:
        data = D.get_base_data()
        data['goods'] = api_response['goods']
        data['category'] = api_response['category']
        return render('goods-category.html', title=api_response['category']['rus_name'], data=data)
    return server_error(message=api_response['message'])


@app.route('/re_restore/<string:category>/<int:goods_id>', methods=["GET", "POST"])
def full_goods(category, goods_id):
    data = D.get_data(base_req=True)
    if not data:
        return server_error()

    api_response = goodsAPI.get([goods_id])
    if not api_response['success']:
        return error(message=api_response['message'])
    data.update(api_response['data'])

    t = api_response['data']['goods']['name']
    curr_admin = verify_curr_admin()

    if request.method == "GET":
        if curr_admin:
            return render('goods-admin.html', title=t, data=data)
        return render('goods.html', title=t, data=data)
    if request.method == "POST":
        if 'sign-in' in request.form:
            return sign_in('goods.html', t, data)
        if 'addToBasket' in request.form:
            # add_to_basket(request.form)
            pass


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


def error(err=520, message='Что-то пошло не так :('):
    data = D.get_data(base_req=True)
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
        if type(form[i]) is list and i not in ['photo', 'photos']:
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
orderAPI = Order()
authorizationAPI = Authorization()

D = DataTemplate()

if __name__ == '__main__':
    db.create_all()

    # new_goods = GoodsModel(name="iPad 2017", description="Full description", short_description="Short description",
    #                        price=26000, count=100, photos="1.png", category="tablets")
    # db.session.add(new_goods)
    # db.session.commit()
    #
    # new_order = OrderModel(
    #   total=52000, user_id=1,
    #   goods={'goods': [{'about': GoodsModel.query.filter_by(id=1).first().to_dict(full_link_req=True),
    #                     'count': 7}]},
    # )
    # db.session.add(new_order)
    # db.session.commit()

    # category = CategoryModel(name="tablets")
    # db.session.add(category)
    # db.session.commit()

    api.add_resource(Authorization, '/authorization')
    api.add_resource(User, '/users/<path:r>')
    api.add_resource(Goods, '/goods/<path:r>')
    api.add_resource(Order, '/order/<path:r>')

    app.run(port=PORT, host=HOST)
