from flask_wtf import Form
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired


class SettingsForm(Form):
    reddit_token = StringField('reddit_token', validators=[DataRequired()])
    evernote_token = StringField('evernote_token')
    upload_to_evernote = BooleanField('upload_to_evernote', default=False)
