from django.contrib.auth.hashers import check_password, make_password
from .special import *

SYMBOLS = {i for i in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#%*"}


# оформить ошибку в changed и errors
def write_error(err, field, changed, errors):
    changed[field] = False
    errors[field] = err


# оформить запись об успешном выполнении в changed
def write_change(field, changed, errors):
    changed[field] = True
    if field in errors:
        errors.pop(field)  # убираем запись из ошибок


# изменение информации пользователя (его профиля) для сервиса RestAPI
def change_user_info_api(user, params, data):

    def ch_first_name(val, *args):
        val = val.strip()
        if val == user.first_name:
            write_error("Nothing to change", *args)
        elif len(val) > 30:
            write_error("Too long (>30 symbols)", *args)
        else:
            user.first_name = val
            write_change(*args)

    def ch_last_name(val, *args):
        val = val.strip()
        if val == user.last_name:
            write_error("Nothing to change", *args)
        elif len(val) > 30:
            write_error("Too long (>150 symbols)", *args)
        else:
            user.last_name = val
            write_change(*args)

    def ch_phone(val, *args):
        phone = str(val).strip()
        plus = phone[0] == '+'
        phone = phone.strip('+')
        if phone.isdigit() and (phone[0] == '7' or (phone[0] in '89' and not plus)):
            if phone[0] in '78' and len(phone) == 11:
                phone = '+7' + phone[1:]
            elif len(phone) == 10 and phone[0] == '9':
                phone = '+7' + phone
            else:
                write_error("Incorrect format", *args)
        else:
            write_error("Incorrect format", *args)
        if phone == user.profile.phone:
            write_error("Nothing to change", *args)
        else:
            # занятость номера телефона
            if Profile.objects.filter(phone=phone).exists():
                write_error("Already used", *args)
            # при отсутствии ошибок
            if not errors['phone_change']:
                user.profile.phone = phone
                write_change(*args)

    def ch_email(val, *args):
        val = val.strip()
        if val == user.email:
            write_error("Nothing to change", *args)
        elif len(val) > 254:
            write_error("Too long (>254 symbols)", *args)
        elif User.objects.filter(email=val).exists():
            write_error("Already used", *args)
        else:
            user.email = val
            write_change(*args)

    def ch_username(val, *args):
        val = val.strip()
        if val == user.username:
            write_error("Nothing to change", *args)
        elif len(val) > 150:
            write_error("Too long (>150 symbols)", *args)
        elif User.objects.filter(username=val).exists():
            write_error("Already used", *args)
        else:
            user.username = val
            write_change(*args)

    def ch_password(val, *args):
        if len(val) > 100:
            write_error("Too long (>100 symbols)", *args)
        elif len(val) < 7:
            write_error("Too short (<7 symbols)", *args)
        else:
            # проверка на лишние символы
            odd_symbols = {i for i in val.upper()} - SYMBOLS
            if odd_symbols:
                write_error(f"Incorrect symbols: {', '.join(odd_symbols)}", *args)
            # одинаковые старый и новый пароли
            elif check_password(val, user.password):
                write_error("Nothing to change", *args)
            else:
                user.set_password(val)
                write_change(*args)

    def ch_email_subscription(val, *args):
        val = get_bool(val)
        if val == user.profile.email_subscription:
            write_error("Nothing to change", *args)
        else:
            user.profile.email_subscription = val
            write_change(*args)

    def ch_photo(val, *args):
        photo_file = data.get(val)
        if not photo_file:
            # ищем по базовому полю
            photo_file = data.get('photo')
        if not photo_file:
            write_error(f"Photo field '{val}' missed in data", *args)
        else:
            photo_path = to_path('profiles', f"{user.id}.png")
            try:
                ext = photo_file.name.split('.')[-1]
                if ext.lower() not in ['png', 'jpg', 'jpeg']:
                    raise ExtensionError
                save_photo(photo_file, photo_path)
                user.has_photo = True
                write_change(*args)
            except ExtensionError:
                write_error(f"Incorrect extension {ext}", *args)
            except SizeError:
                if os.path.exists(photo_path):
                    os.remove(photo_path)  # удаляем часть, что успела записаться
                write_error("Size > 10Mb", *args)
            except Exception as e:
                logger.error(f"Save photo (change user info <api>) error: {e}")
                write_error("Unknown Error", *args)
                if os.path.exists(photo_path):  # если что-то успело сохраниться
                    os.remove(photo_path)  # удаляем на всякий случай

    changed = dict()
    errors = dict()
    all_fields = {
        'first_name_change': lambda val: ch_first_name(val, 'first_name_change', changed, errors),
        'last_name_change': lambda val: ch_last_name(val, 'last_name_change', changed, errors),
        'phone_change': lambda val: ch_phone(val, 'phone_change', changed, errors),
        'email_change': lambda val: ch_email(val, 'email_change', changed, errors),
        'username_change': lambda val: ch_username(val, 'username_change', changed, errors),
        'password_change': lambda val: ch_password(val, 'password_change', changed, errors),
        'email_subscription_change': lambda val: ch_email_subscription(val, 'email_subscription_change',
                                                                       changed, errors),
        'photo_change': lambda val: ch_photo(val, 'photo_change', changed, errors)
    }
    try:
        fields = {key for key in all_fields} & {key for key in params}  # пересечения параметров
        if not fields:
            return False, "Empty change params", changed, errors

        for field in fields:
            changed[field] = None
            all_fields[field](params.get(field))  # вызываем функцию изменения у каждого параметра

        # если хоть одно изменение было успешным
        if any(filter(lambda field: changed[field], changed)):
            if save_with_date(user):  # в случае успеха сохранения
                return True, 'Ok', changed, errors
            else:
                return False, 'Server Error, all changes canceled', changed, errors
        # в противном случае
        return False, "Nothing was changed", changed, errors

    except Exception as e:
        logger.error(f"Change user info <api> error: {e}")
        return False, 'Server Error, changes may be canceled', changed, errors


# поиск пользователей по параметрам
def find_users_with_params_api(params):
    # все возможные параметры для пользователя и его профиля
    user_params = {
        'id', 'is_active',
        'first_name', 'last_name'
    }
    profile_params = {
        'email_subscription', 'has_photo'
        'is_users_editor', 'is_goods_editor'
    }

    n_users = params.pop('n', 5)  # сколько выдать пользователей
    full_req = get_bool(params.pop('full', False))  # подробная информация о каждом

    sorting = get_users_sort(params.pop('sort', ID_SORT))  # ключ сортировки
    reverse_sorting = get_bool(params.pop('reverse_sort', False))  # обратная сортировка

    params_keys = {key for key in params}

    # находим пересечения переданных параметров со всеми возможными для поиска
    user_params = dict(
        map(optimize_params_keys, [(p, params.pop(p)) for p in user_params & params_keys])
    )
    # то же самое для Profile
    profile_params = dict(
        map(optimize_params_keys, [(p, params.pop(p)) for p in profile_params & params_keys])
    )

    # при отсутствии совпадений
    if not (user_params or profile_params):
        return False, "Incorrect params", []

    # оптимизация номера телефона
    if 'phone' in profile_params:
        # в однозначном варианте
        profile_params['phone'] = optimize_phone(str(profile_params['phone']))
    elif 'phone__in' in profile_params:
        # в многозначном варианте
        # оптимизируем каждый переданный номер телефона
        phones = profile_params['phone__in']
        for i in range(len(phones)):
            phones[i] = optimize_phone(phones[i])

    # осуществляем поиск по переданным параметрам
    users_data = set(
        map(lambda user: user.profile,  # преобразуем в модель Profile
            User.objects.filter(is_superuser=False, **user_params).all())
    )

    profiles_data = set(
        filter(lambda profile: not profile.user.is_superuser,  # убираем суперпользователей
               Profile.objects.filter(**profile_params).all())
    )

    # находим результат (совпадения или что-то одно,
    # в зависимости от переданных параметров)
    if user_params and profile_params:
        result = users_data & profiles_data  # пересечения
    else:
        result = users_data if user_params else profiles_data  # или что-то одно

    # сортируем и обрезаем до n_users
    result = list(sorted(result, key=sorting, reverse=reverse_sorting))[:n_users]
    # преобразуем полные/краткие (full_req) данные в словари
    result = list(map(lambda r: r.to_dict(all_req=full_req, api=True), result))

    if result:
        return True, "Ok", result
    else:
        # делаем красивое сообщение о том, что ничего не найдено
        user_params.update(profile_params)
        user_params = '; '.join([f'{p}={user_params[p]}' for p in user_params])
        message = f"Users with params '{user_params}' do not exist"
        return True, message, []

