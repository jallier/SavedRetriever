import praw
from flask import Flask, render_template, url_for, request, flash, redirect
from flask_sqlalchemy import SQLAlchemy

from Resources.forms import SettingsForm

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

# import models so db knows where the models are
from Resources import models


@app.route("/")
def main():
    return render_template('index.html', posts={1, 2, 3, 4, 5})


@app.route("/settings", methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    reddit_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first()
    if not form.validate_on_submit():
        flash("Please enter keys for required services")
    return render_template('settings.html', form=form, reddit_token=reddit_token, imgur_token=None,
                           readability_token=None, evernote_token=None)


@app.route("/reddit_wizard")
def reddit_wizard():
    client_id = '_Nxh9h0Tys5KCQ'
    response_type = 'code'
    state = '1'
    redirect_uri = 'http://127.0.0.1:5000/authorize_callback'
    scope = 'identity history read'
    duration = 'permanent'
    refresh_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first().setting_value
    return render_template('reddit_wizard.html', client_id=client_id, response_type=response_type, state=state,
                           redirect_uri=redirect_uri, scope=scope, duration=duration,
                           refresh_token=refresh_token)


@app.route("/authorize_callback")
def authorize_callback():
    from Resources import reddit_oauth_wizard as auth
    refresh_token = auth.reddit_oauth_wizard(request.args.get('code'))
    reddit_db_entry = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first()
    if reddit_db_entry is None:
        s = models.Settings(setting_name='reddit_refresh_token', setting_value=refresh_token, setting_type=0,
                            token_authorised=True)
        db.session.add(s)
    else:
        s = reddit_db_entry
        s.setting_value = refresh_token
    db.session.commit()

    return reddit_wizard()


@app.route('/test')
def test():
    CLIENT_ID = '_Nxh9h0Tys5KCQ'
    redirect_uri = 'http://127.0.0.1:5000/authorize_callback'

    refresh_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first().setting_value

    r = praw.Reddit('Saved Retriever Installed by /u/fuzzycut')
    r.set_oauth_app_info(CLIENT_ID, '', redirect_uri)

    access_information = r.refresh_access_information(refresh_token)
    r.set_access_credentials(**access_information)

    return r.get_me().name


if __name__ == "__main__":
    app.run(debug=True)
