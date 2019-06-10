from rest_framework.views import APIView
from django.contrib.auth.models import User
from special import *
from os import path


# оптимизация переданных в запросе параметров {'param': ['e']} -> {'param': 'e'};
# {'param': ['e1', 'e2', 'e3']}
# strict=True -> {'param': 'e1'};
# strict=False  -> {'param': ['e1', 'e2', 'e3']}
def optimize_params(params, strict=True):
    for arg in params:
        if type(params[arg]) is list and \
                (strict or (not strict and len(params[arg]) == 1)):
            params[arg] = params[arg][0]


def make_token(user):
    pass


def unmake_token(user):
    pass


class UserAPI(APIView):
    """ API для получения / редактирования / удаления данных пользователей. """
    def get(self, req, request):
        # params = dict(request.query_params)
        # optimize_params(params)
        # # проверка на введение корректного токена
        # pass
        # # получение полных данных конкретного пользователя
        # if req == 'me':
        #     if not str(user_id).isdigit():
        #         return make_success(False, "user_id field incorrect")
        #     user = User.objects.filter(id=user_id)
        #     # проверка на существование пользователя
        #     if not user:
        #         return make_success(False, message=f"User {user_id} does not exist")
        #     # проверка на собственника учетной записи / админа
        #     if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
        #         return make_success(False, message="Access Error")
        #     return make_success(user=user.to_dict(all_req=True))
        #
        # elif req == 'one':
        #     if 'user_id' not in data:
        #         return make_success(False, "user_id field unfilled")
        #     user_id = data['user_id']
        #     if not str(user_id).isdigit():
        #         return make_success(False, "user_id field incorrect")
        #     user = User.objects.filter(id=user_id)
        #     # проверка на существование пользователя
        #     if not user:
        #         return make_success(False, message=f"User {user_id} does not exist")
        #     # проверка на собственника учетной записи / админа
        #     if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
        #         return make_success(False, message="Access Error")
        #     return make_success(user=user.to_dict(all_req=True))
        #
        # # получение кратких данных всех пользователей (админ)
        # if 'all' in params:
        #     if not verify_curr_admin(a):
        #         return make_success(False, message='Access Error')
        #     try:
        #         return make_success(users=[i.to_dict(name_req=True, surname_req=True,
        #                                              phone_req=True, email_req=True,
        #                                              login_req=True) for i in UserModel.query.all()])
        #     except Exception as e:
        #         logging.error("UserAPI Error (get all):\t{}".format(e))
        #         return make_success(False, message='Server Error')
        return make_success(False, message='Bad request')
    #
    # def put(self, r, a=None, params=dict(), request_data=None):
    #     params = params if params else dict(request.args)
    #     optimize_params(params)
    #     a = a if a else get_authorization(params=params)
    #
    #     arg = str(r).lower().strip(' /')
    #     if arg.isdigit():
    #         errors = {'name': None,
    #                   'surname': None,
    #                   'phone': None,
    #                   'email': None,
    #                   'check_password': None,
    #                   'new_password': None,
    #                   'photo': None}
    #         try:
    #             user_id = int(arg)
    #             parser = reqparse.RequestParser()
    #             for arg in ('name', 'surname', 'email', 'check_password', 'new_password', 'subscription', 'photo'):
    #                 parser.add_argument(arg)
    #             args = parser.parse_args()
    #             if request_data:
    #                 args.update(request_data)
    #
    #             user = UserModel.query.filter_by(id=user_id).first()
    #             if not user:
    #                 return make_success(False, message="User {} doesn't exist".format(user_id))
    #
    #             # проверка на собственника учетной записи / админа
    #             if not (verify_curr_admin(a) or (int(a['id']) == user_id and verify_authorization(a=a))):
    #                 return make_success(False, message="Access Error")
    #
    #             # редактирование фото
    #             if 'photo' in args and args['photo']:
    #                 photo = None
    #                 try:
    #                     ext = args['photo'].filename.split('.')[-1]
    #                     if ext.lower() in ['png', 'jpg', 'jpeg']:
    #                         photo = 'static/profiles/{}.png'.format(user.id)
    #                         args['photo'].save(photo)
    #                         user.photo = '1'
    #                         user.date_changes = curr_time()
    #                         db.session.commit()
    #                     else:
    #                         raise TypeError
    #                 except Exception as e:
    #                     logging.error("Save photo (change user info) Error:\t{}".format(e))
    #                     if photo and path.exists(photo):
    #                         remove(photo)
    #                         errors['photo'] = "Ошибка при загрузке фото."
    #
    #             # проверка на ввод подтверждающего пароля
    #             # для возможности дальнейшего редактирования личных данных
    #             if 'check_password' not in args or not args['check_password']:
    #                 if 'photo' in args and args['photo']:  # если редактировалось только фото
    #                     return make_success(errors=errors)
    #                 errors['check_password'] = "Введите старый пароль для подтверждения."
    #                 return make_success(False, errors=errors)
    #
    #             # проверка подтверждающего пароля
    #             if not check_password_hash(user.password, args['check_password']):
    #                 errors['check_password'] = "Старый пароль введен неверно."
    #                 return make_success(False, errors=errors)
    #
    #             # обработка поступивших данных
    #             if args['name'] and args['name'] != user.name:
    #                 if len(args['name']) > 80:
    #                     errors['name'] = "Слишком длинное имя (> 80 символов)."
    #                 else:
    #                     user.name = args['name'].strip()
    #             if args['surname'] and args['surname'] != user.surname:
    #                 if len(args['surname']) > 80:
    #                     errors['surname'] = "Слишком длинная фамилия (> 80 символов)."
    #                 else:
    #                     user.surname = args['surname'].strip()
    #
    #             if args['phone'] and args['phone'] != user.phone:
    #                 phone = str(args['phone']).strip()
    #                 plus = phone[0] == '+'
    #                 phone = phone.strip('+')
    #                 if phone.isdigit() and (phone[0] == '7' or (phone[0] in '89' and not plus)):
    #                     if phone[0] in '78' and len(phone) == 11:
    #                         phone = '+7' + phone[1:]
    #                     elif len(phone) == 10 and phone[0] == '9':
    #                         phone = '+7' + phone
    #                     else:
    #                         errors['phone'] = "Некорректный номер телефона."
    #                 else:
    #                     errors['phone'] = "Некорректный формат номера телефона."
    #                 # занятость номера телефона
    #                 if UserModel.query.filter_by(phone=phone).first():
    #                     errors['phone'] = "Номер телефона занят. Введите другой."
    #                 # при отсутствии ошибок
    #                 elif not errors['phone']:
    #                     user.phone = phone
    #
    #             if args['email'] and args['email'] != user.email:
    #                 if len(args['email']) > 120:
    #                     errors['email'] = "Слишком длинный e-mail (> 120 символов)."
    #                 else:
    #                     user.email = args['email'].strip()
    #             if args['new_password']:
    #                 if len(args['new_password']) > 100:
    #                     errors['new_password'] = "Слишком длинный пароль (> 100 символов)."
    #                 elif len(args['new_password']) < 3:
    #                     errors['new_password'] = "Слишком простой пароль (< 3 символов)."
    #                 else:
    #                     user.password = generate_password_hash(args['new_password'].strip())
    #
    #             user.subscription = 1 if args['subscription'] else 0  # подписка на новости
    #
    #             db.session.commit()
    #             return make_success(errors=errors)
    #         except Exception as e:
    #             logging.error("Change user info Error:\t{}".format(e))
    #             return make_success(False, 'Server error')
    #
    #     return make_success(False, 'Bad request')
    #
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



