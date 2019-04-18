from flask import Flask, render_template, redirect, request, make_response, url_for
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
    description = db.Column(db.String(2000), nullable=False)
    short_description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(150), nullable=False)
    photos = db.Column(db.String(500))

    def __repr__(self):
        return '<Goods {} {} {}руб {}шт>'.format(self.id, self.name, self.price, self.count)

    def to_dict(self, id_req=True, name_req=True, description_req=False,
                short_description_req=True, price_req=True, count_req=False,
                category_req=True, full_link_req=False, photos_req=False):
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
        if category_req:
            d['category'] = self.category
        if full_link_req:
            d['full_link'] = '{}/{}/{}'.format(HOME, self.category.strip('/'), self.id)
        if photos_req:
            d['photos'] = [photo.strip() for photo in self.photos.split(';')]
        return d


class CategoryModel(db.Model):
    name = db.Column(db.String(150), unique=True, primary_key=True)

    def __repr__(self):
        return '<Category {}>'.format(self.name)


class OrderModel(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    total = db.Column(db.Float, nullable=False)
    goods = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(10), default="processing")
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'), nullable=False)
    user = db.relationship('UserModel', backref=db.backref('OrderModel'))

    def __repr__(self):
        return '<Order {} {}руб>'.format(self.id, self.total)

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
        return '<User {} {} {} {}>'.format(self.id, self.login, self.name, self.surname)

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
        return {'menu_items': [{'name': 'Планшеты',
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

    def get_main_data(self):
        return {'slides': [url_for('static', filename='main_banners/{}.png'.format(i + 1)) for i in range(4)],
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

    def get_lk_data(self, tmp_a=None):
        response = userAPI.get((tmp_a if tmp_a else get_authorization())['id'], a=tmp_a)
        if response['success']:
            return {'user': response['user'],
                    'errors': {'change_profile_info': {'name': None,
                                                       'surname': None,
                                                       'email': None,
                                                       'check_password': None,
                                                       'new_password': None,
                                                       'photo': None}},
                    }

    def get_lk_admin_data(self, tmp_a=None):
        goods_response = goods_listAPI.get()
        orders_response = order_listAPI.get(tmp_a)
        users_response = user_listAPI.get(tmp_a)
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


def get_authorization(tmp_id=None, tmp_login=None, tmp_password=None, img=False):
    a = {'id': tmp_id if tmp_id else request.cookies.get('userID'),
         'login': tmp_login if tmp_login else request.cookies.get('userLogin'),
         'password': tmp_password if tmp_password else request.cookies.get('userPassword')}
    if img and a['id']:
        user = UserModel.query.filter_by(id=a['id']).first()
        if user:
            a.update(user.to_dict(photo_req=True))
        else:
            a['photo'] = 'static/profiles/NoPhoto.jpg'
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
            print("Authorization (API) Error:\t", e)
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
            print("Registration (API) Error:\t", e)
            errors['other'] = "Ошибка сервера."
            return make_success(False, message="Server error", errors=errors)


class User(Resource):
    def get(self, user_id, a=None):
        user = UserModel.query.filter_by(id=user_id).first()
        # проверка на существование
        if not user:
            return make_success(False, message="User doesn't exist")
        # проверка на собственника учетной записи / админа
        a = a if a else get_authorization()
        if not (verify_curr_admin(a) or (a['id'] == user_id and verify_authorization(a=a))):
            return make_success(False, message="Access Error")
        return make_success(user=user.to_dict(all_req=True))

    def put(self, user_id, request_data=None, a=None):
        errors = {'name': None,
                  'surname': None,
                  'email': None,
                  'check_password': None,
                  'new_password': None,
                  'photo': None}
        try:
            parser = reqparse.RequestParser()
            for arg in ('name', 'surname', 'email', 'check_password', 'new_password', 'subscription', 'photo'):
                parser.add_argument(arg)
            args = parser.parse_args()
            if request_data:
                args.update(request_data)

            user = UserModel.query.filter_by(id=user_id).first()
            if not user:
                return make_success(False, message="User doesn't exist")

            # проверка на собственника учетной записи / админа
            a = a if a else get_authorization()
            if not (verify_curr_admin(a) or (a['id'] == user_id and verify_authorization(a=a))):
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

    def delete(self, user_id, a=None):
        # проверка на собственника учетной записи / админа
        a = a if a else get_authorization()
        if not (verify_curr_admin(a) or (a['id'] == user_id and verify_authorization(a=a))):
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
            return make_success(False, message="User doesn't exist")
        except Exception as e:
            print("User delete Error:\t", e)
            return make_success(False, message="Server Error")


class UserList(Resource):
    def get(self, tmp_a=None):
        if not verify_curr_admin(tmp_a):
            return make_success(False, message='Access Error')
        try:
            return make_success(users=[i.to_dict(name_req=True, surname_req=True,
                                                 email_req=True, login_req=True) for i in UserModel.query.all()])
        except:
            return make_success(False, message='Server Error')


class Goods(Resource):
    def get(self):
        pass

    def put(self):
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
        pass

    def delete(self, goods_id, a=None):
        # проверка на админа
        a = a if a else get_authorization()
        if not verify_curr_admin(a):
            return make_success(False, message="Access Error")
        try:
            goods = GoodsModel.query.filter_by(id=goods_id).first()
            if goods:
                db.session.delete(goods)
                db.session.commit()
                return make_success()
            return make_success(False, message="Goods doesn't exist")
        except Exception as e:
            print("Goods delete Error:\t", e)
            return make_success(False, message="Server Error")


class GoodsList(Resource):
    def get(self):
        try:
            return make_success(goods=[i.to_dict(full_link_req=True) for i in GoodsModel.query.all()])
        except Exception as e:
            print(e)
            return make_success(False, message='Server Error')

    def post(self, request_data=None):
        all_fields = ['name', 'description', 'short_description',
                      'price', 'count', 'category']
        errors = dict()
        for field in all_fields:
            errors[field] = None

        try:
            if not verify_curr_admin():
                return make_success(False, message="Access error")

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
            if len(args['short_description']) > 200:
                errors['short_description'] = "Краткое описание должно быть не более 200 символов."
            if len(args['category']) > 150:
                errors['category'] = "Категория не должна превышать 150 символов."

            if any(err for err in errors.values()):
                return make_success(False, message="Too much data", errors=errors)

            if not CategoryModel.query.filter_by(name=args['category']).first():
                c = CategoryModel(name=args['category'])
                db.session.add(c)

            # правильный формат количества и цены
            err = False
            for val_type, field in ((int, 'count'), (float, 'price')):
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
            print("Add goods (API) Error:\t", e)
            return make_success(False, message="Server error", errors=errors)


class Order(Resource):
    def delete(self, *args, a=None):
        if not args[0].isdigit():
            return make_success(False, message="Null request")
        try:
            order_id = int(args[0])
            order = OrderModel.query.filter_by(id=order_id).first()
            if order:
                # проверка на собственника учетной записи / админа
                a = a if a else get_authorization()
                if not (verify_curr_admin(a) or (a['id'] == order.user_id and verify_authorization(a=a))):
                    return make_success(False, message="Access Error")
                db.session.delete(order)
                db.session.commit()
                return make_success()
            return make_success(False, message="Order doesn't exist")
        except Exception as e:
            print("Order delete Error:\t", e)
            return make_success(False, message="Server Error")

    def put(self, *args, a=None):
        if not args[0].isdigit() or len(args) < 2 or \
                args[1] not in ('processing', 'cancel', 'done'):
            return make_success(False, message="Bad request")
        try:
            order_id = int(args[0])
            order = OrderModel.query.filter_by(id=order_id).first()
            if order:
                # проверка на админа
                a = a if a else get_authorization()
                if not verify_curr_admin(a):
                    return make_success(False, message="Access Error")
                order.status = args[1]
                db.session.commit()
                return make_success()
            return make_success(False, message="Order doesn't exist")
        except Exception as e:
            print("Order put Error:\t", e)
            return make_success(False, message="Server Error")


class OrdersList(Resource):
    def get(self, tmp_a=None):
        if not verify_curr_admin(tmp_a):
            return make_success(False, message='Access Error')
        try:
            return make_success(orders=[i.to_dict() for i in OrderModel.query.all()])
        except Exception as e:
            print(e)
            return make_success(False, message='Server Error')


def make_success(state=True, message='Ok', **kwargs):
    data = {'success': state if state else False}
    if message:
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
def category(category):
    return render('/')


@app.route('/re_restore/<string:category>/<int:goods_id>')
def goods(category, goods_id):
    return render('/')


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
        return error()

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
            return error()

        if request.method == 'POST':
            if 'changeUserInfoBtn' in request.form:
                response = userAPI.put(get_authorization()['id'], request_data=get_request_data())
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])
            elif 'photo' in request.files:
                response = userAPI.put(get_authorization()['id'], request_data=get_request_data(files=True))
                data = D.get_data(base_req=True, lk_req=True)
                data['errors']['change_profile_info'].update(response['errors'])

        return render("lk.html", title=t, data=data)
    return redirect(HOME)


@app.route('/lk-admin', methods=["GET", "POST"])
def lk_admin():
    t = "Личный кабинет (ADMIN)"
    if verify_curr_admin():
        data = D.get_data(base_req=True, lk_admin_req=True)
        if not data:
            return error()
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
                response = goods_listAPI.post(request_data=form)
                if not response['success']:
                    err['add_goods'] = response['errors']
                    last['add_goods'] = form
                    category = 'addGoods'
            elif 'deleteGoodsBtn' in form:
                category = 'goods'
                resp = goodsAPI.delete(form['goodsID'])
                if not resp['success']:
                    err['add_data']['goods'] = resp['message']
            elif 'deleteOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.delete(form['orderID'])
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'cancelOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put(form['orderID'], 'cancel')
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'doneOrderBtn' in form:
                category = 'orders'
                resp = orderAPI.put(form['orderID'], 'done')
                if not resp['success']:
                    err['add_data']['orders'] = resp['message']
            elif 'deleteUserBtn' in form:
                category = 'users'
                resp = userAPI.delete(form['userID'])
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


def render(template, a=None, **kwargs):
    authorization = a if a else get_authorization(img=True)
    if (not a) and (not verify_authorization(admin=True)):
        sign_out()
        return render_template(template, authorization=get_authorization(), **kwargs)
    return render_template(template, authorization=authorization, **kwargs)


HOME = '/re_restore'
HOST = '127.0.0.1'
PORT = 8080

# данные админа
ADMIN_ID = -1
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"

# Все API
userAPI = User()
user_listAPI = UserList()
goodsAPI = Goods()
goods_listAPI = GoodsList()
orderAPI = Order()
order_listAPI = OrdersList()
authorizationAPI = Authorization()

D = DataTemplate()

if __name__ == '__main__':
    db.create_all()

    # new_goods = GoodsModel(name="iPad 2017", description="Full description", short_description="Short description",
    #                        price=26000, count=100, photos="1.png", category="tablets")
    # db.session.add(new_goods)
    # db.session.commit()
    #
    # new_order = OrderModel(total=52000, user_id=1,
    #                        goods={'goods': [{'about': GoodsModel.query.filter_by(id=1).first().to_dict(full_link_req=True),
    #                                          'count': 7}]},
    #                        )
    # db.session.add(new_order)
    # db.session.commit()

    # category = CategoryModel(name="tablets")
    # db.session.add(category)
    # db.session.commit()

    api.add_resource(Authorization, '/authorization')
    api.add_resource(UserList, '/users')
    api.add_resource(User, '/users/<int:user_id>')
    api.add_resource(GoodsList, '/goods')
    # api.add_resource(Goods, '/goods/<int:goods_id>')
    api.add_resource(OrdersList, '/order')
    api.add_resource(Order, '/order/<path:args>')

    app.run(port=PORT, host=HOST)
