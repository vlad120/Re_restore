from django.contrib.auth.models import User
from MainSite.models import Category, Product, Order, Profile
from django.contrib.auth.hashers import check_password, make_password
from special import *

SYMBOLS = {i for i in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#%*"}


# оформить ошибку в changed и errors
def write_error(err, field, changed, errors):
    changed[field] = False
    errors[field] = err


# оформить запись об успешном выполнении
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

    def ch_subscription(val, *args):
        if val.lower() in {'true', 't', '+'}:
            val = True
        elif val.lower() in {'false', 'f', '-'}:
            val = False
        else:
            write_error("Incorrect value", *args)
        if val == user.profile.subscription:
            write_error("Nothing to change", *args)
        else:
            user.profile.subscription = val
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
                user.photo = True
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
        'subscription_change': lambda val: ch_subscription(val, 'subscription_change', changed, errors),
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
