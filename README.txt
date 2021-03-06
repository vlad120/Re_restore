 ------------------------------------------------------
|   New:Store Web Server version 1.3.3 (11/05/2019)   |
 ------------------------------------------------------

© Миронов В.А., интернет-магазин электроники "New:Store". Все права защищены.


Для запуска сервера необходимо запустить скрипт "app.py".
Необходимы:
    - Версия Python 3.3 и новее
    - Дополнительные библиотеки:
        - flask
        - flask_restful
        - flask_sqlalchemy



Запросы к API:

    'users':    GET:        '<user_id>'   -  получение полных данных коркретного пользователя (обязательна авторизация).
                            'all'         -  получение кратких данных всех пользователей (обязательна авторизация админа).
                PUT:        '<user_id>'   -  изменение данных пользователя, в параметрах передаются: 'name', 'surname', 'email', 'check_password', 'new_password', 'subscription', 'photo' (обязательна авторизация).
                DELETE:     '<user_id>'   -  удаление учетной записи пользователя (обязательна авторизация).


    'goods':    GET:        '<goods_id>'  -  получение полных данных коркретного товара.
                            'all'         -  получение краткой информации обо всех товарах.
                            'random'      -  получение случайных товаров, по умолчанию одного, в параметрах можно указать количество 'n'.
                            'category'    -  получение всех товаров из категории, в параметрах указывается категория 'category', возможно указать способ сортироваки 'sort' ('NEW' - по новизне, 'CHE' - мначала дешевые, 'EXP' - сначала дорогие).
                POST:       'new'         -  создание нового товара, необходимые параметры: 'name', 'description', 'short_description', 'price', 'count', 'category', 'rus_category' (обязательна авторизация админа).
                PUT:        '<goods_id>'  -  изменение данных о товаре, параметры: 'rus_category', 'category', 'name', 'price', 'count', 'short_description', 'description', 'add_photo', 'delete_photo' (обязательна авторизация админа).
                DELETE:     '<goods_id>'  -  удаление товара и всех его данных (обязательна авторизация админа).


    'search':   GET         'id'          -  поиск товаров по их артикулу (id), параметр - 'id'
                            'name'        -  по имени, параметр - 'name'
                            'description' -  по описанию, параметр - 'description'
                            'auto'        -  автоматический поиск по всем параметрам, параметр - 'text'


    'basket':   GET:        'curr'        -  получение корзины текущего пользователя, включая товары и итоговую сумму (обязательна авторизация).
                POST:       '<goods_id>'  -  добавление товара в корзину пользователя.
                PUT:        '<goods_id>'  -  изменение количества товара в корзине, обязательный параметр количества 'count': (число | 'all') (обязательна авторизация).
                DELETE:     '<goods_id>'  -  удаление товара из корзины пользвателя (обязательна авторизация).


    'orders':   GET:        'all'         -  получение всех заказов (обязательна авторизация админа).
                            'user'        -  получение всех заказов конкретного пользователя, обязательный параметр 'user_id'.
                POST:       'curr'        -  сделать заказ из текущей корзины пользователя (обязательна авторизация).
                PUT:        '<order_id>'  -  редактирвоание статуса заказа, обязательный параметр 'status': ('done' | 'delivered' | 'cancel') (обязательна авторизация).
                DELETE:     '<order_id>'  -  удаление заказа (обязательна авторизация).


    'authorization':        POST - регистрация нового пользователя, обязательны параметры: 'name', 'surname', 'email', 'login', 'password'.
                            GET - автризация пользователя, обязательные параметры: 'login', 'password'.  // можно использовать в качестве проверки на существование пользователя в системе (т.к. данные сохраняются на протяжении сеанса только с помощью cookies)


    # Там, где необходима авторизация, к параметрам добавляем 'authorization=login;password', где 'login' - логин пользователя, 'password' - пароль.

    # Формат запроса:      "<адрес к серверу>/api/<название api>/<запрос>"

    # Примеры запроса:     GET 'http://127.0.0.1:8080/api/goods/4'
                           GET 'http://127.0.0.1:8080/api/goods/all/?authorization=admin;admin'
                           GET 'http://127.0.0.1:8080/api/search/auto/?text=ipad'
                           PUT 'http://127.0.0.1:8080/api/users/9/?authorization=admin;admin&email=someemail@mail.ru&check_password=qwerty'



Обратная связь:
    E-mail: dkflbckfd-2600@mail.ru


История версий:

    1.3.3:
        - Изменения в БД (добавление новых связанных сущностей, новый принцип работы с товарами).
        - Рестайлинг страницы личного кабинета.
        - Новый логотип магазина.
        - Оптимизация кода и исправление ошибок.

    1.3.2:
        - Новая логика работы с файловой системой для товаров.
          (теперь у каждого есть своя папка, где хранятся только его фотографии, разбиение по категориям убрано).
        - Оптимизировано хранение данных о фотографиях в БД.
        - Исправление незначительных ошибок.

    1.3.1:
        - Исправлены ошибки работы с файловаой системой, неизвестные ошибки при регистрации.
        - Убран "мусор" из папки проекта.
        - Теперь в аккаунте пользователя есть номер телефона (для обратной связи после заказа товара).
        - Обновлен ассортимент товаров.
        - Общая оптимизация.

    1.3.0:
        - Добавлен поиск по товарам на сайте (в шапке сайта).
        - Обновлен дизайн подвала – добавлены разделы 'Контакты' и 'Помощь покупателю'.

    1.2.1:
        - Улучшен алгоритм поискового API.
        - Добавлен поиск по id товара.
        - Исправление всех известных ошибок.

    1.2.0:
        - Изменен принцип работы с JSON-форматом в БД для оптимизации под хостинг.
        - Добавлен API для поиска товаров.
        - Мелкие исправления и улучшения.

    1.1.0:
        - Исправление ошибок и повышение безопасности API.
    1.0.3:
        - Исправление ошибок с API - полная переработка.
    1.0.2:
        - Исправлены некоторые ошибки.
    1.0.1:
        - Оптимизация API.
    1.0.0:
        - Первая версия, основной функционал сайта.
