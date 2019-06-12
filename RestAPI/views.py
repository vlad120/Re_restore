from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from MainSite.models import Category, Product, Order, Profile
from django.contrib.auth.hashers import check_password, make_password
from special import *
from datetime import datetime


# оптимизация переданных в запросе параметров {'param': ['e']} -> {'param': 'e'};
# {'param': ['e1', 'e2', 'e3']}
# strict=True -> {'param': 'e1'};
# strict=False  -> {'param': ['e1', 'e2', 'e3']}
def get_params(request, strict=True):
    params = dict(request.query_params)
    for arg in params:
        if type(params[arg]) is list and \
                (strict or (not strict and len(params[arg]) == 1)):
            params[arg] = params[arg][0]
    return params


def check_token(params):
    token = params.get('token')
    if not token:
        return False, "token missed"
    try:
        profile = Profile.objects.get(token=token)
        return True, profile.user
    except Profile.DoesNotExist:
        return False, "token is wrong"


class AuthorizationAPI(APIView):
    """ API для получения токена / регистрации пользователей. """
    def get(self, request, req):
        if req not in {'getToken'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            # получение полных данных конкретного пользователя
            if req == 'getToken':
                # переданы ли логин и пароль
                username = params.get('username')
                password = params.get('password')
                if not username or not password:
                    return make_success(False, "username/password missed")
                # находим пользователя с переданными данными
                user = authenticate(username=username, password=password)
                if user is None:
                    return make_success(False, "Wrong username/password")
                # суперпользователь не может получить токен
                if user.is_superuser:
                    return make_success(False, "Access Error")
                user.profile.token = make_token()
                user.profile.date_changes = datetime.now()
                user.save()
                return make_success(token=user.profile.token)

        except Exception as e:
            logger.error(f"AuthorizationAPI (r: {req}) error: {e}")
            return make_success(False, "Server Error")


class UserAPI(APIView):
    """ API для получения / редактирования / удаления данных пользователей. """
    def get(self, request, req):
        if req not in {'me', 'one', 'params', 'all'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            check = check_token(params)  # корректность токена
            if check[0]:
                token_user = check[1]
            else:
                return make_success(False, check[1])

            # получение своих данных
            if req == 'me':
                user_data = token_user.profile.to_dict(all_req=True)
                user_data['photo'] = make_url(user_data['photo'])  # абсолютный путь
                return make_success(user=user_data)

            # ограничение доступа
            if not token_user.is_staff:
                return make_success(False, "Access Error")

            # получение полных данных конкретного пользователя
            if req == 'one':
                keys = ['id', 'username', 'email']
                for k in keys:
                    if k in params:
                        params = {k: params[k]}
                        keys = None  # индикатор, что нужный ключ нашёлся
                        break
                if keys:
                    return make_success(False, f"{'/'.join(keys)} missed")
                try:
                    user = User.objects.get(is_superuser=False, **params)
                except User.DoesNotExist:
                    return make_success(False, f"user {k}={params[k]} does not exist")

                user_data = user.profile.to_dict(all_req=True)
                user_data['photo'] = make_url(user_data['photo'])  # абсолютный путь
                return make_success(user=user_data)

            # получение списка пользователей с заданными параметрами
            if req == 'params':
                params.pop('token')  # оставляем только параметры для поиска
                if not params:
                    return make_success(False, f"Parameters missed")
                # отделяем параметры для профиля пользователя в  profile_params
                profile_fields = Profile.get_all_fields()
                profile_params = {}
                for p in params:
                    if p in profile_fields:
                        profile_params[p] = params[p]
                for p in profile_params:
                    params.pop(p)  # оставляем в params только параметры для пользователя
                try:
                    users_data1 = set(map(lambda u: u.profile,  # преобразование в профиль
                                          User.objects.filter(is_superuser=False, **params).all()))\
                        if params else None
                    users_data2 = set(Profile.objects.filter(is_superuser=False, **profile_params).all())\
                        if profile_params else None

                    # собираем результаты
                    if params and profile_params:
                        users_data = users_data1 & users_data2
                    else:
                        users_data = users_data1 if params else users_data2
                    # преобразуем в данные
                    users_data = list(map(lambda p: p.to_dict(), users_data))

                except Exception as e:  # FieldError
                    print(e)
                    return make_success(False, "Incorrect params")

                if users_data:
                    message = "Ok"
                else:
                    # делаем красивое сообщение
                    params.update(profile_params)
                    params = '; '.join([f'{p}={params[p]}' for p in params])
                    message = f"users with params {params} do not exist"
                return make_success(message=message, users=users_data)

            # получение кратких данных всех пользователей
            if req == 'all':
                return make_success(
                    users=[u.profile.to_dict() for u in User.objects.filter(is_superuser=False).all()]
                )
        except Exception as e:
            logger.error(f"UserAPI (r: {req}) error: {e}")
            return make_success(False, "Server Error")

    def put(self, request, req):
        if req not in {'me', 'one'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            check = check_token(params)  # корректность токена
            if check[0]:
                token_user = check[1]
            else:
                return make_success(False, check[1])

            data = request.data

            errors = {'first_name': None,
                      'last_name': None,
                      'phone': None,
                      'email': None,
                      'username': None,
                      'new_password': None,
                      'check_password': None,
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
                    photo = None
                    try:
                        ext = args['photo'].filename.split('.')[-1]
                        if ext.lower() in ['png', 'jpg', 'jpeg']:
                            photo = 'static/profiles/{}.png'.format(user.id)
                            args['photo'].save(photo)
                            user.photo = '1'
                            user.date_changes = curr_time()
                            db.session.commit()
                        else:
                            raise TypeError
                    except Exception as e:
                        logging.error("Save photo (change user info) Error:\t{}".format(e))
                        if photo and path.exists(photo):
                            remove(photo)
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

                if args['phone'] and args['phone'] != user.phone:
                    phone = str(args['phone']).strip()
                    plus = phone[0] == '+'
                    phone = phone.strip('+')
                    if phone.isdigit() and (phone[0] == '7' or (phone[0] in '89' and not plus)):
                        if phone[0] in '78' and len(phone) == 11:
                            phone = '+7' + phone[1:]
                        elif len(phone) == 10 and phone[0] == '9':
                            phone = '+7' + phone
                        else:
                            errors['phone'] = "Некорректный номер телефона."
                    else:
                        errors['phone'] = "Некорректный формат номера телефона."
                    # занятость номера телефона
                    if UserModel.query.filter_by(phone=phone).first():
                        errors['phone'] = "Номер телефона занят. Введите другой."
                    # при отсутствии ошибок
                    elif not errors['phone']:
                        user.phone = phone

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

        except Exception as e:
            logger.error(f"AuthorizationAPI (r: {req}) error: {e}")
            return make_success(False, "Server Error")
        return make_success(False, "Bad request")

    # def delete(self, r, a=None, params=dict()):
    #     params = params if params else dict(request.args)
    #     optimize_params(params)
    #     a = a if a else get_authorization(params=params)
    #
    #     arg = str(r).lower().strip(' /')
    #     if arg.isdigit():
    #         user_id = int(arg)
    #         # проверка на собственника учетной записи / админа
    #         if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
    #             return make_success(False, message="Access Error")
    #         try:
    #             user = UserModel.query.filter_by(id=user_id).first()
    #             if user:
    #                 # удаляем фото профиля
    #                 photo = 'static/profiles/{}.png'.format(arg)
    #                 if path.exists(photo):
    #                     remove(photo)
    #                 # удаляем все заказы пользователя
    #                 for order in OrderModel.query.filter_by(user_id=user_id).all():
    #                     db.session.delete(order)
    #                 db.session.delete(user)
    #                 db.session.commit()
    #                 return make_success()
    #             return make_success(False, message="User {} doesn't exist".format(user_id))
    #         except Exception as e:
    #             logging.error("User delete Error:\t{}".format(e))
    #             return make_success(False, message="Server Error")
    #
    #     return make_success(False, message='Bad request')



