from flask import Flask, render_template, redirect, request, make_response, jsonify, url_for
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from forms import SignUpForm, AddNewsForm
from datetime import date
import requests
from copy import deepcopy
from os import remove

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

news_sorting = 'DATE'

DATA = {'menu_items': [{'name': 'tablets',
                        'link': '#'},
                       {'name': 'Смартфоны',
                        'link': '#'}],
        'errors': {'authorization': {'password': None,
                                     'login': None,
                                     'other': None,
                                     'any': False}},
        'last': {'authorization': {'login': '',
                                   'password:': '',
                                   'remember': True}}
        }


def get_authorization(tmp_id=None, tmp_login=None, tmp_password=None, img=False):
    a = {'id': tmp_id if tmp_id else request.cookies.get('userID'),
         'login': tmp_login if tmp_login else request.cookies.get('userLogin'),
         'password': tmp_password if tmp_password else request.cookies.get('userPassword')}
    if img and a['id']:
        try:
            a['image'] = UserModel.query.filter_by(id=a['id']).first().photo if a['id'] else None
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
    if authorization:
        return render_template(template, authorization=authorization, **kwargs)
    else:
        return render_template(template, **kwargs)


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
    photo = db.Column(db.String(100), nullable=False, default="NoPhoto.jpg")

    def __repr__(self):
        return '<User {} {} {} {}>'.format(self.id, self.login, self.name, self.surname)

    def to_dict(self, id_req=True, name_req=False, surname_req=False,
                email_req=False, login_req=True, photo_req=False):
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
        if photo_req:
            d['photo'] = self.photo
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
        all_fields = ['name', 'surname', 'email', 'login', 'password', 'photo']
        errors = dict()
        for field in all_fields + ['other']:
            errors[field] = None

        try:
            if get_authorization()['id']:
                return make_success(False)

            parser = reqparse.RequestParser()
            for field in all_fields:
                parser.add_argument(field)
            args = dict(parser.parse_args())

            # проверка на пустоту
            err = False
            for field in all_fields:
                if not args[field] and field != 'photo':
                    errors[field] = 'Поле должно быть заполнено.'
                    err = True
            if err:
                return make_success(False, errors=errors)

            # на занятый логин
            if (args['login'] == admin_login or
                    UserModel.query.filter_by(login=args['login']).first()):
                errors['login'] = "Логин занят другим пользователем. Придумайте другой"

            # на длину полей (для базы данных)
            if len(args['name']) > 80:
                errors['name'] = "Слишком длинное имя (максимум 80 символов)"
            if len(args['surname']) > 80:
                errors['surname'] = "Слишком длинная фамилия (максимум 80 символов)"
            if len(args['email']) > 120:
                errors['email'] = "Слишком длинный e-mail (максимум 120 символов)"
            if len(args['login']) > 80 and not errors['login']:
                errors['login'] = "Слишком длинный логин (максимум 80 символа)"
            if len(args['password']) > 100:
                errors['password'] = "Слишком длинный пароль (максимум 100 символов)"
            if len(args['password']) < 3:
                errors['password'] = "Слишком простой пароль (не менее 3 символов)"

            if any(err for err in errors.values()):
                return make_success(False, errors=errors)

            photo_name = None
            if args['photo']:
                try:
                    ext = request.files['file'].filename.split('.')[-1]
                    if ext.lower() in ['png', 'jpg', 'jpeg']:
                        photo_name = 'tmp.{}'.format(ext)
                        args['photo'].save('static/profiles/' + photo_name)
                except Exception as e:
                    print("Save photo during registration Error:\t", e)
                    if photo_name:
                        remove(photo_name)
                        photo_name = None

            if not photo_name:
                photo_name = "NoPhoto.jpg"
            args['photo'] = photo_name

            args['password'] = generate_password_hash(args['password'])

            new_user = UserModel(**args)
            db.session.add(new_user)
            db.session.commit()

            return make_success(new_user.id, errors=errors)
        except Exception as e:
            print("Registration (API) Error:\t", e)
            errors['other'] = "Ошибка сервера."
            return make_success(False, errors=errors)


class News(Resource):
    def get(self, news_id):
        news_id = int(news_id)
        exist = news_exist(news_id)
        if not exist[0]:
            return exist[1]
        news = NewsModel.query.filter_by(id=news_id).first().to_dict(content_req=True,
                                                                     author_id_req=True)
        return make_response(render('full-news.html', title=news['title'], data={'news': news}))

    def delete(self, news_id):
        news_id = int(news_id)
        exist = news_exist(news_id)
        if not exist[0]:
            return exist[1]
        try:
            news = NewsModel.query.filter_by(id=news_id).first()
            db.session.delete(news)
            db.session.commit()
            return {'success': 'OK'}
        except:
            return {'success': 'FAIL'}


class NewsList(Resource):
    def get(self):
        s = "id" if news_sorting == "DATE" else "title"
        news = [i.to_dict(short_content_req=True) for i in NewsModel.query.order_by(s).all()]
        data = {'news': news if news_sorting == "ABC" else list(reversed(news)),
                'news_sorting': news_sorting}
        return make_response(render('news.html', title="News", data=data))

    def post(self):
        # изменение сортировки новостей на главной странице
        if 'sorting' in request.form:
            return self.put()
        # или добавление новых новостей
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('title', required=True)
            parser.add_argument('content', required=True)
            parser.add_argument('author_id', required=True, type=int)
            args = parser.parse_args()
            news = NewsModel(title=args['title'], content=args['content'],
                             author_id=args['author_id'], date=date.today())
            db.session.add(news)
            db.session.commit()
            return success()
        except:
            return success(False)

    def put(self):
        global news_sorting
        args = request.form
        news_sorting = args['sorting']
        return self.get()


class User(Resource):
    def get(self, user_id):
        user_id = int(user_id)
        exist = user_exist(user_id)
        if not exist[0]:
            return success(False)
        user = UserModel.query.filter_by(id=user_id).first().to_dict(name_req=True,
                                                                     surname_req=True,
                                                                     email_req=True)
        return success(user=user)

    def put(self, user_id):
        try:
            user_id = int(user_id)
            parser = reqparse.RequestParser()
            for arg in ('name', 'surname', 'email', 'login', 'password'):
                parser.add_argument(arg)
            args = parser.parse_args()
            if not any(val for val in args.values()):
                return success(False, 'Bad request')
            user = UserModel.query.filter_by(id=user_id).first()
            if args['name']:
                user.name = args['name']
            if args['surname']:
                user.surname = args['surname']
            if args['email']:
                user.email = args['email']
            if args['login']:
                user.login = args['login']
            if args['password']:
                user.password = generate_password_hash(args['password'])
            db.session.commit()
            return success()
        except:
            return success(False, 'Server error')

    def delete(self, user_id):
        user_id = int(user_id)
        if get_authorization()['id'] == admin_id:
            exist = user_exist(user_id)
            if not exist[0]:
                return success(False, 'User not found')
            try:
                user = UserModel.query.filter_by(id=user_id).first()
                db.session.delete(user)
                db.session.commit()
                return success()
            except:
                return success(False, 'Server error')
        return success(False, 'Access error')


class UsersList(Resource):
    def get(self):
        try:
            users = [i.to_dict(name_req=True,
                               surname_req=True,
                               login_req=True) for i in UserModel.query.all()]
            return success(users=users)
        except:
            return success(False, 'Server error')

    def post(self):
        try:
            parser = reqparse.RequestParser()
            for arg in ('name', 'surname', 'email', 'login', 'password'):
                parser.add_argument(arg, required=True)
            args = self.parser.parse_args()
            user = NewsModel(name=args['name'], surname=args['surname'],
                             email=args['email'], login=args['login'],
                             password=generate_password_hash(args['password']))
            db.session.add(user)
            db.session.commit()
            return make_success()
        except:
            return make_success(False)


class PublishNews(Resource):
    errors = {'title': None,
              'content': None}

    def get(self):
        authorization = get_authorization()['id']
        if authorization and authorization != admin_id:
            form = AddNewsForm()
            return self.render(form)

    def post(self):
        authorization = get_authorization()['id']
        if authorization and authorization != admin_id:
            form = AddNewsForm()
            if form.validate_on_submit():
                title = form.title.data
                content = form.content.data

                if len(title) > 70:
                    self.errors['title'] = "Слишком длинное название (должно быть не более 70 символов)"
                if len(content) > 4000:
                    self.errors['content'] = "Слишком много контента (должно быть не более 4000 символов)"

                if any(err for err in self.errors.values()):
                    return self.render(form)

                r = 'http://{}:{}/{}'.format(host, port, "news")
                data = {'title': title,
                        'content': content,
                        'author_id': authorization,
                        'date': str(date.today())}

                if requests.post(r, json=data).json()['success'] == "OK":
                    return redirect('/lk')
                return make_response(server_error)
            return self.render(form)

    def render(self, form):
        return make_response(render("add-news.html", title="Add News", form=form, data={'errors': self.errors}))


def make_success(state=True, message='', **kwargs):
    data = {'success': state if state else False}
    if message:
        data['message'] = message
    data.update(kwargs)
    return jsonify(data)


@app.route('/re_restore', methods=["GET", "POST"])
def re_restore():
    t = 'Добро пожаловать в Re_restore!'
    data = deepcopy(DATA)

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

    try:
        response = get_self_response('/authorization', data=ready_data if ready_data else request.form, method='GET')
        if response['success']:
            a = get_authorization(response['success'], request.form['login'], request.form['password'], img=True)
            resp = make_response(render(page, a=a, title=t, data=data))
            resp.set_cookie('userID', str(a['id']))
            resp.set_cookie('userLogin', str(a['login']))
            resp.set_cookie('userPassword', str(a['password']))
        else:
            data['errors']['authorization'].update(response['errors'])
            data['errors']['authorization']['any'] = True
            data['last']['authorization']['login'] = request.form['login']
            data['last']['authorization']['password'] = request.form['password']
            data['last']['authorization']['remember'] = True if 'remember_me' in request.form else False
            resp = make_response(render(page, title=t, data=data))
        return resp
    except Exception as e:
        print("Sign In (func) Error:\t", e)
        return server_error()


@app.route('/sign-out')
def sign_out():
    resp = make_response(redirect('/re_restore'))
    for cookie in ('userID', 'userLogin', 'userPassword'):
        resp.set_cookie(cookie, '', expires=0)
    return resp


@app.route('/sign-up', methods=["GET", "POST"])
def sign_up():
    if get_authorization()['id']:
        return redirect('/lk')
    t = 'Регистрация'
    all_fields = ['name', 'surname', 'email', 'login', 'password', 'photo']

    try:
        data = deepcopy(DATA)
        data['last']['registration'] = dict()
        data['errors']['registration'] = dict()
        for field in all_fields:
            data['last']['registration'][field] = ''
            data['errors']['registration'][field] = None
        data['errors']['registration']['other'] = None

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
    except Exception as e:
        print("Sign Up (func) Error:\t", e)
        return server_error()


@app.route('/lk', methods=["GET", "POST"])
def lk():
    t = "Личный кабинет"
    verify_authorization()
    authorization = get_authorization()
    if authorization['id'] == admin_id:
        return render('lk_admin.html', title=t, data=DATA)
    elif authorization:
        return render("lk.html", title=t, data=DATA)
    return redirect('/re_restore')


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
    data = deepcopy(DATA)
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
    return redirect('/re_restore')


if __name__ == '__main__':
    db.create_all()

    # new_user = UserModel(name='dfs',
    #                      surname='erdfscsa',
    #                      email='resdaafghrgfds',
    #                      login='vlad',
    #                      password=generate_password_hash('qwerty'),
    #                      photo='NoPhoto.jpg')
    # db.session.add(new_user)
    # db.session.commit()

    api.add_resource(Authorization, '/authorization')

    api.add_resource(UsersList, '/users')
    api.add_resource(User, '/users/<int:user_id>')
    api.add_resource(PublishNews, '/add-news')

    app.run(port=port, host=host)
