from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .db_models_funcs import *


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
        if profile.user.is_active:
            return True, profile.user
        return False, "User was deleted"
    except Profile.DoesNotExist:
        return False, "token is wrong"


def find_user(params):
    keys = ['id', 'username', 'email']
    for k in keys:
        if k in params:
            params = {k: params[k]}
            keys = None  # индикатор, что нужный ключ нашёлся
            break
    if keys:
        return False, f"{'/'.join(keys)} missed"
    try:
        return True, User.objects.get(is_superuser=False, **params)
    except User.DoesNotExist:
        return False, f"user {k}={params[k]} does not exist"


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
                if not user.is_active:
                    return make_success(False, "User was deleted")
                user.profile.token = make_token()
                save_with_date(user.profile)
                return make_success(token=user.profile.token)

        except Exception as e:
            logger.error(f"AuthorizationAPI (get: {req}) error: {e}")
            return make_success(False, "Server Error")


class UserAPI(APIView):
    """ API для получения / редактирования данных пользователей. """
    def get(self, request, req):
        if req not in {'me', 'one', 'params', 'all'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            ok, result = check_token(params)  # корректность токена
            if ok:
                token_user = result
            else:
                return make_success(False, result)

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
                search = find_user(params)
                if not search[0]:
                    return make_success(False, search[1])
                user = search[1]

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
            logger.error(f"UserAPI (get: {req}) error: {e}")
            return make_success(False, "Server Error")

    def put(self, request, req):
        if req not in {'me', 'one'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            ok, result = check_token(params)  # корректность токена
            if ok:
                token_user = result
            else:
                return make_success(False, result)

            if req == 'me':
                user = token_user
            elif req == 'one':
                # безопасность
                if not (token_user.is_staff and token_user.profile.is_users_editor):
                    return make_success(False, "Access Error")
                search = find_user(params)
                if not search[0]:
                    return make_success(False, search[1])
                user = search[1]

            ok, message, changed, errors = change_user_info_api(user, params, request.data)
            # при успехе
            if ok:
                return make_success(message=message, changed=changed, errors=errors)
            # в противном случае
            return make_success(False, message=message, changed=changed, errors=errors)
        except Exception as e:
            logger.error(f"UserAPI (put: {req}) error: {e}")
            return make_success(False, "Server Error")

    def delete(self, request, req):
        if req not in {'me', 'one'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request)
            ok, result = check_token(params)  # корректность токена
            if ok:
                token_user = result
            else:
                return make_success(False, result)

            if req == 'me':
                user = token_user
            elif req == 'one':
                # безопасность
                if not (token_user.is_staff and token_user.profile.is_users_editor):
                    return make_success(False, "Access Error")
                search = find_user(params)
                if not search[0]:
                    return make_success(False, search[1])
                user = search[1]
            if not user.is_active:
                return make_success(False, "User has already been deleted")
            # защита персонала и суперпользователей
            if user.is_staff or user.is_superuser:
                return make_success(False, "Access Error")
            # дезактивируем учетную запись
            user.is_active = False
            save_with_date(user)
            return make_success()
        except Exception as e:
            logger.error(f"UserAPI (delete: {req}) error: {e}")
            return make_success(False, "Server Error")

