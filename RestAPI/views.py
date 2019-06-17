from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .db_models_funcs import *


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
        if req not in {'me', 'one', 'all', 'params'}:
            return make_success(False, "Bad request")
        try:
            params = get_params(request, find_complex=True)
            ok, result = check_token(params)  # корректность токена
            if ok:
                token_user = result
            else:
                return make_success(False, result)

            # получение своих данных
            if req == 'me':
                user_data = token_user.profile.to_dict(all_req=True, api=True)
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

                return make_success(user=user.profile.to_dict(all_req=True, api=True))

            # получение кратких/полных данных всех пользователей
            if req == 'all':
                return make_success(
                    users=[u.profile.to_dict(all_req=params.get('full'), api=True)
                           for u in User.objects.filter(is_superuser=False).all()]
                )

            # поиск пользователей по параметрам
            if req == 'params':
                if not params:
                    return make_success(False, f"Parameters missed")

                ok, message, users_data = find_users_with_params_api(params)
                return make_success(ok, message, users=users_data)

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
                # защита персонала и суперпользователей от изменения их данных
                if user.is_staff or user.is_superuser:
                    return make_success(False, "Access Error")

            ok, message, changed, errors = change_user_info_api(user, params, request.data)
            return make_success(ok, message, changed=changed, errors=errors)

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


class ProductAPI(APIView):
    """ API для получения данных о товаре,
        размещения / редактирования / удаления товаров. """
    def get(self, request, req):
        if req not in {'one', 'all', 'params'}:
            return make_success(False, "Bad request")
        try:
            pass
        except Exception as e:
            logger.error(f"ProductAPI (get: {req}) error: {e}")
            return make_success(False, "Server Error")

    def put(self, request, req):
        if req not in {'one', 'params'}:
            return make_success(False, "Bad request")
        try:
            pass
        except Exception as e:
            logger.error(f"ProductAPI (put: {req}) error: {e}")
            return make_success(False, "Server Error")

    def delete(self, request, req):
        if req not in {'one', 'params'}:
            return make_success(False, "Bad request")
        try:
            pass
        except Exception as e:
            logger.error(f"ProductAPI (delete: {req}) error: {e}")
            return make_success(False, "Server Error")

