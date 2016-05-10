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
    # schedule_day = SelectField('schedule_day', choices=[("1", "Monday"), ("2", "Tuesday"), ("3", "Wednesday"),
    #                                                     ("4", "Thursday"), ("5", "Friday"), ("6", "Saturday"),
    #                                                     ("7", "Sunday")])
    schedule_hour = SelectField('schedule_hour', choices=[(str(x), str(x))for x in range(0, 24)])
    schedule_min = SelectField('schedule_min', choices=[(str(x), format(x, '02d'))for x in range(0, 60)])
