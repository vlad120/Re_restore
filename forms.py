from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired

data_required = "Это поле обязательно."


class SignUpForm(FlaskForm):
    name = StringField(validators=[DataRequired(data_required)])
    surname = StringField(validators=[DataRequired(data_required)])
    email = StringField(validators=[DataRequired(data_required)])
    login = StringField(validators=[DataRequired(data_required)])
    password = PasswordField(validators=[DataRequired(data_required)])
    photo = FileField()
    submit = SubmitField('Зарегистрироваться')


class AddNewsForm(FlaskForm):
    title = StringField(validators=[DataRequired(data_required)])
    content = TextAreaField(validators=[DataRequired(data_required)])
    submit = SubmitField('Готово')
