from flask_wtf import Form
from wtforms import StringField, BooleanField, IntegerField, SelectField
from wtforms.validators import DataRequired


class SettingsForm(Form):
    reddit_token = StringField('reddit_token', validators=[DataRequired()])
    evernote_token = StringField('evernote_token')
    upload_to_evernote = BooleanField('upload_to_evernote', default=False)
    number_of_comments = IntegerField('number_of_comments', default=5)
    save_comments = BooleanField('save_comments', default=False)
    number_of_posts = IntegerField("number_of_posts", default=20)
    color = SelectField('color', choices=[("red", "Red"), ("blue", 'Blue'), ("purple", "Purple"), ("green", "Green"),
                                          ("yellow", "Yellow")])
    cron_string = StringField('cron_string')


class LoginForm(Form):
    username = StringField('username', validators=[DataRequired()], default="admin")
    password = StringField('password')
