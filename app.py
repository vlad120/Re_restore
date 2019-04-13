from flask import Flask, render_template, redirect, request, make_response, jsonify, url_for
from flask_restful import reqparse, Api, Resource
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from forms import SignInForm, SignUpForm, AddNewsForm
from datetime import date
import requests
from copy import deepcopy

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
        'last': {'login': '',
                 'password:': ''}
        }


def get_authorization():
    a = Authorization.query.filter_by(ip=request.remote_addr).first()
    return a.id if a else None


def add_authorization(user_id):
    a = Authorization(ip=request.remote_addr, id=user_id)
    db.session.add(a)
    db.session.commit()


def del_authorization(user_id=None, curr=False):
    if curr:
        a = Authorization.query.filter_by(ip=request.remote_addr).first()
    elif user_id:
        a = Authorization.query.filter_by(id=user_id).first()
    db.session.delete(a)
    db.session.commit()


def render(template, **kwargs):
    authorization = get_authorization()
    if authorization == admin_id:
        return render_template(template, authorization=admin_id, login=admin_login, **kwargs)
    elif authorization:
        user_login = UserModel.query.filter_by(id=authorization).first().login
        return render_template(template, authorization=authorization, login=user_login, **kwargs)
    else:
        return render_template(template, **kwargs)


class Authorization(db.Model):
    ip = db.Column(db.CHAR(15), primary_key=True, nullable=False)
    id = db.Column(db.Integer, nullable=False)


class NewsModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(70), unique=False, nullable=False)
    content = db.Column(db.String(4000), unique=False, nullable=False)
    author_id = db.Column(db.Integer, unique=False, nullable=False)
    date = db.Column(db.String(10), unique=False, nullable=False)

    def __repr__(self):
        return '<News {} {}>'.format(self.id, self.title)

    def to_dict(self, id_req=True, title_req=True, content_req=False,
                short_content_req=False, author_id_req=False, date_req=True):
        d = dict()
        if id_req:
            d['id'] = self.id
        if title_req:
            d['title'] = self.title
        if content_req:
            d['content'] = self.content
        if short_content_req:
            d['content'] = self.content[:150] + " ..." if len(self.content) > 150 else self.content
        if author_id_req:
            d['author_id'] = self.author_id
        if date_req:
            d['date'] = self.date
        return d


class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    surname = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), unique=False, nullable=False)

    def __repr__(self):
        return '<Student {} {} {} {}>'.format(self.id, self.username, self.name, self.surname)

    def to_dict(self, id_req=True, login_req=True, name_req=False,
                surname_req=False, email_req=False):
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
        return d


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
        if get_authorization() == admin_id:
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
            return success()
        except:
            return success(False)


class PublishNews(Resource):
    errors = {'title': None,
              'content': None}

    def get(self):
        authorization = get_authorization()
        if authorization and authorization != admin_id:
            form = AddNewsForm()
            return self.render(form)

    def post(self):
        authorization = get_authorization()
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


class LK(Resource):
    def get(self):
        authorization = get_authorization()
        if authorization == admin_id:
            data = requests.get('http://{}:{}/{}'.format(host, port, "users")).json()
            if data['success'] == 'OK':
                return make_response(render('lk_admin.html', title="LK ADMIN", data=data))
            return server_error()
        elif authorization:
            data = dict()
            user = UserModel.query.filter_by(id=authorization).first().to_dict(name_req=True,
                                                                               surname_req=True,
                                                                               email_req=True)
            data['user'] = user
            news = [news.to_dict(content_req=True) for news in NewsModel.query.filter_by(author_id=authorization).all()]
            data['news'] = reversed(news)
            return make_response(render("lk.html", title="LK", data=data))
        return redirect('/sign-in')

    def post(self):
        authorization = get_authorization()
        if not authorization:
            return access_error()
        args = request.form
        if 'delete_news' in args:
            news_id = args['delete_news']
            exist = news_exist(news_id)
            if not exist[0]:
                return exist[1]
            if NewsModel.query.filter_by(id=news_id).first().author_id == authorization:
                r = 'http://{}:{}/{}/{}'.format(host, port, "news", news_id)
                if requests.delete(r).json()['success'] == "OK":
                    return self.get()
                return server_error()
            return access_error()
        elif 'add_news' in args:
            if authorization != admin_id:
                return redirect('/add-news')
            return access_error()
        elif 'delete_user' in args:
            if authorization == admin_id:
                try:
                    response = requests.delete('http://{}:{}/{}/{}'.format(host, port,
                                                                           "users", args['delete_user'])).json()
                    if response['success'] == 'OK':
                        return redirect('/lk')
                    return error(message=response['message'])
                except:
                    return server_error()
            return access_error()
        return self.get()


class SignUp(Resource):
    errors = {'name': None,
              'surname': None,
              'email': None,
              'login': None,
              'password': None}

    def get(self):
        authorization = get_authorization()
        if not authorization:
            form = SignUpForm()
            return self.render(form)
        return redirect('/lk')

    def post(self):
        authorization = get_authorization()
        if not authorization:
            form = SignUpForm()
            if form.validate_on_submit():
                name = form.name.data
                surname = form.surname.data
                email = form.email.data
                login = form.login.data
                password = form.password.data

                if (login == admin_login or
                        UserModel.query.filter_by(login=login).first()):
                    self.errors['login'] = "Логин занят другим пользователем. Придумайте другой"

                if len(name) > 64:
                    self.errors['name'] = "Слишком длинное имя (максимум 80 символов)"
                if len(surname) > 64:
                    self.errors['surname'] = "Слишком длинная фамилия (максимум 80 символов)"
                if len(login) > 64 and not self.errors['login']:
                    self.errors['login'] = "Слишком длинный логин (максимум 80 символа)"
                if len(password) > 100:
                    self.errors['password'] = "Слишком длинный пароль (максимум 100 символов)"
                if len(password) < 3:
                    self.errors['password'] = "Слишком простой пароль (не менее 3 символов)"

                if any(err for err in self.errors.values()):
                    return self.render(form)

                new_user = UserModel(name=name,
                                     surname=surname,
                                     email=email,
                                     login=login,
                                     password=generate_password_hash(password))
                db.session.add(new_user)
                db.session.commit()
                add_authorization(new_user.id)
                return redirect('/lk')
            return self.render(form)
        return redirect('/lk')

    def render(self, form):
        return make_response(render("sign-up.html", title="Sign Up", form=form, data={'errors': self.errors}))


class SignIn(Resource):
    def get(self):
        response = {'success': False,
                    'errors': {'already_authorized': False,
                               'password': None,
                               'login': None,
                               'other': None}
                    }
        try:
            if get_authorization():
                response['errors']['already_authorized'] = True
                return response

            parser = reqparse.RequestParser()
            for arg in ('login', 'password'):
                parser.add_argument(arg, required=True)
            args = parser.parse_args()
            login = args['login']
            password = args['password']

            if login == admin_login and password == admin_password:
                add_authorization(admin_id)
                response['success'] = True
                return response

            user = UserModel.query.filter_by(login=login).first()
            if user:
                if check_password_hash(user.password, password):
                    add_authorization(user.id)
                    response['success'] = True
                    return response
                response['errors']['password'] = "Неправильный пароль."
            else:
                response['errors']['login'] = "Логин не найден в системе."
        except:
            response['success'] = False
            response['errors']['other'] = "Ошибка сервера."
        return response


class SignOut(Resource):
    def get(self):
        del_authorization(curr=True)
        return redirect("/news")


def success(state=True, message='', **kwargs):
    data = {'success': 'OK' if state else 'FAIL'}
    if message:
        data['message'] = message
    data.update(kwargs)
    return jsonify(data)


def user_exist(user_id):
    if UserModel.query.filter_by(id=user_id).first():
        return True, None
    return False, error(404, 'Пользователь {} не найден :('.format(user_id))


def news_exist(news_id):
    if NewsModel.query.filter_by(id=news_id).first():
        return True, None
    return False, error(404, 'Новость {} не найдена :('.format(news_id))


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
            sign_in(data)
        return render('index.html', title=t, data=data)


def sign_in(data):
    response = get_self_response('/sign-in', data=dict(request.form))
    if not response['success']:
        data['errors']['authorization'].update(response['errors'])
        data['errors']['authorization']['any'] = True
        data['last']['login'] = request.form['login']
        data['last']['password'] = request.form['password']


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
    return render('error.html', data={'message': message, 'type': err})


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

    api.add_resource(SignIn, '/sign-in')
    api.add_resource(SignUp, '/sign-up')
    api.add_resource(SignOut, '/sign-out')

    api.add_resource(UsersList, '/users')
    api.add_resource(User, '/users/<int:user_id>')
    api.add_resource(LK, '/lk')
    api.add_resource(PublishNews, '/add-news')

    app.run(port=port, host=host)
