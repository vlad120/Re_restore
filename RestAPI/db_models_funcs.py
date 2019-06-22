from django.contrib.auth.hashers import check_password, make_password
from .special import *

SYMBOLS = {i for i in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#%*"}
STRIP = " ,.;:\"\'!@#$%^&*()"


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
    def make_return(state=True, m="Ok", u=[]):
        return state, m, u

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
    active_only = get_bool(params.pop('active_only', True))  # найти только активных

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
        return make_return(False, "Incorrect params", [])

    # оптимизация номера(-ов) телефона(-ов)
    if 'phone' in profile_params:
        # в однозначном варианте
        profile_params['phone'] = optimize_phone(str(profile_params['phone']))
    elif 'phone__in' in profile_params:
        # в многозначном варианте
        # оптимизируем каждый переданный номер телефона
        phones = profile_params['phone__in']
        for i in range(len(phones)):
            phones[i] = optimize_phone(phones[i])

    # переформатируем параметры профиля для filter
    profile_params = dict(('profile__' + p, profile_params[p]) for p in profile_params)
    user_params.update(profile_params)  # объединяем параметры
    # осуществляем поиск
    result = set(User.objects.filter(user__is_superuser=False,
                                     user__is_active=active_only,
                                     **user_params).all())

    # сортируем и обрезаем до n_users
    result = list(sorted(result, key=sorting, reverse=reverse_sorting))[:n_users]
    # преобразуем полные/краткие (full_req) данные в словари
    result = list(map(lambda r: r.profile.to_dict(all_req=full_req, api=True), result))

    if result:
        return make_return(u=result)
    else:
        # делаем красивое сообщение о том, что ничего не найдено
        user_params.update(profile_params)
        user_params = '; '.join([f'{p}={user_params[p]}' for p in user_params])
        message = f"Users with params '{user_params}' do not exist"
        return make_return(m=message)


# поиск товаров по параметрам
def find_products_with_params_api(params, full_access=False):
    def make_return(state=True, m="Ok", p=[], p_no=[], total_found=0):
        return state, m, p, p_no, total_found

    def write_incorrect(p):
        errors[p] = "Incorrect"

    def check_range(lst, p, val_type, *checks):
        # проверка на количество (2 для range) и на нужный тип значений
        if len(lst) != 2 or not set(filter(lambda val: type(val) is val_type, lst)):
            write_incorrect(p)
            return False
        # дополнительные проверки
        if checks:
            for check in checks:
                for i in lst:  # перебираем каждый элемент (их 2) отдельно
                    if not check(i):
                        return False
        return True

    # все возможные параметры
    product_params = {
        'category', 'count', 'bought',
        'len_photos', 'price', 'search'
    }

    errors = dict()

    range_products = params.pop('range', (0, 12))  # с какого по какой выдать товар
    check_range(range_products, 'range', int, lambda val: val > 0)

    full_req = get_bool(params.pop('full', False))  # подробная информация о каждом
    available_only = get_bool(params.pop('available_only', True))  # найти только, что в наличии

    active_only = get_bool(params.pop('active_only', True))  # найти только активные
    if not active_only and not full_access:  # проверка на доступ к просмотру неактивных товаров
        active_only = True

    sorting = get_products_sort(params.pop('sort', ID_SORT))  # ключ сортировки
    reverse_sorting = get_bool(params.pop('reverse_sort', False))  # обратная сортировка

    params_keys = {key for key in params}

    # находим пересечения переданных параметров со всеми возможными для поиска
    # заодно приводим в нужный тип их значения
    product_params = dict(
        map(optimize_params_keys, [(p, params.pop(p)) for p in product_params & params_keys])
    )

    # при отсутствии совпадений
    if not product_params:
        return make_return(False, "Incorrect params")

    if available_only:
        # если нужны только те, что в наличии
        products = Product.objects.filter(is_active=active_only, count__gt=0, **product_params)
    else:
        products = Product.objects.filter(is_active=active_only, **product_params)

    # фильтр по параметрам с множеством значений
    category = product_params.get('category')
    if category:
        if type(category) is list:
            products = products.filter(category__name__in=category)
        elif type(category) is str:
            products = products.filter(category__name=category)
        else:
            write_incorrect('category')

    # фильтр по параметрам с разбегом значений
    for p in ['count', 'bought', 'len_photos', 'price']:
        curr = product_params.get(p)
        if curr:
            if type(curr) is list:
                if check_range(curr, p, int):
                    filter_params = {p + '__range': tuple(curr)}
                    products = products.filter(**filter_params)
            elif type(curr) is int:
                filter_params = {p: curr}
                products = products.filter(**filter_params)
            else:
                write_incorrect(p)

    # поиск по характеристикам
    characteristics = product_params.get('characteristics')
    if characteristics:
        if type(str) is str:
            if ';' in characteristics and '=' in characteristics:
                characteristics = str_to_properties(characteristics)
                found = set()
                for product in products:
                    p_characteristics = str_to_properties(product.characteristics)
                    ok = True
                    for key in characteristics:
                        # если ключа нет в характеристиках
                        # или занчения характеристик не совпадают
                        if not (key in p_characteristics and
                                characteristics[key] == p_characteristics[key]):
                            ok = False  # пропускаем продукт
                    if ok:
                        found.add(product)
                products = found
            else:
                write_incorrect('characteristics')
        else:
            write_incorrect('characteristics')

    # поиск по id, названию и описанию
    search = product_params.get('search')
    if search:
        result_id = []
        # пытаемся найти по id (артиклу)
        if type(search) is int:
            product = set(filter(lambda pro: pro.id == search, products))
            if product:
                result_id.append(product)
            search = str(search)
        result1 = search_products_by_name(search, products)
        result2 = search_products_by_description(search, products)

        # объединяем результаты
        products = result_id
        for i in range(3):
            products += result1[i] + result2[i]
        # убираем одинаковые
        products = list(frozenset(products))

    # сортируем
    products = frozenset(sorted(products, key=sorting, reverse=reverse_sorting))
    total_found = len(products)  # запоминаем общее количество найденного
    # и обрезаем до нужного нтервала
    try:
        products = products[range_products[0]:range_products[1]]
    except IndexError:
        if total_found > 11:
            products = products[-12:]

    # если нужны товары не в наличии тоже
    if not available_only:
        # выбираем продукты, что не в наличии
        products_no = frozenset(filter(lambda p: p.count > 0, products))
        # убираем их из products
        products = list(products - products_no)
        # преобразуем полные/краткие (full_req) данные в словари
        products_no = list(map(lambda r: r.to_dict(all_req=full_req, api=True), products_no))
        products = list(map(lambda r: r.to_dict(all_req=full_req, api=True), products))
    else:
        products_no = []
        # преобразуем полные/краткие (full_req) данные в словари
        products = list(map(lambda r: r.to_dict(all_req=full_req, api=True), products))

    if products or products_no:
        return make_return(p=products, p_no=products_no, total_found=total_found)
    else:
        # делаем красивое сообщение о том, что ничего не найдено
        product_params = '; '.join([f'{p}={product_params[p]}' for p in product_params])
        message = f"Products with params '{product_params}' do not exist"
        return make_return(m=message)


def search_products_by_name(name, products):
    name = name.lower()  # already stripped
    full = []
    part = []
    consist = []
    for product in products:
        product_name = product.name.lower()
        if product_name == name:
            full.append(product)
        elif name in product_name:
            len_product_name = len(product_name)
            not_found_words = (len_product_name - len(name)) / len_product_name  # % ненайденных слов
            part.append((product, not_found_words))
        else:
            # множества слов в названиях
            name_words = {w for w in name.split()}
            goods_name_words = {w.strip(STRIP) for w in product_name.split()}
            n = len(name_words & goods_name_words)  # количество совпадений
            if n:
                len_name_words = len(name_words)
                not_found_words = (len_name_words - n) / len_name_words  # % ненайденных слов
                consist.append((product, not_found_words))

    # сортируем по количеству (не)найденных слов и оставляем только сами продукты
    part = list(map(lambda p: p[0], sorted(part, key=lambda p: p[1])))
    consist = list(map(lambda c: c[0], sorted(consist, key=lambda c: c[1])))

    # объединяем и возвращаем найденное в порядке соответствия
    return [full, part, consist]


def search_products_by_description(text, products):
    text = text.lower()  # already stripped
    part = []
    consist = []
    text_words = {w.strip(STRIP) for w in text.split()}  # множество слов в тексте
    for product in products:
        description = (product.short_description + ' ' + product.description).lower()
        description_words = {w.strip(STRIP) for w in description.split()}  # множество слов в описании
        if text in description:
            len_description = len(description)
            not_found_words = (len_description - len(text_words)) / len_description  # % ненайденных слов
            part.append((product, not_found_words))
        else:
            n = len(text_words & description_words)
            if n:
                len_text_words = len(text_words)
                not_found_words = (len_text_words - n) / len_text_words  # % ненайденных слов
                consist.append((product, not_found_words))

    # сортируем по количеству (не)найденных слов и оставляем только сами продукты
    part = list(map(lambda p: p[0], sorted(part, key=lambda p: p[1])))
    consist = list(map(lambda c: c[0], sorted(consist, key=lambda c: c[1])))

    # объединяем и возвращаем найденное в порядке соответствия
    return [[], part, consist]
