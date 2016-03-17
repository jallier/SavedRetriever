import logging
from threading import Thread

import praw
from flask import Flask, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy

# import download as DownloadClient
from Resources.forms import SettingsForm

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

# import models so db knows where the models are
from Resources import models
from Resources.DownloadThread import DownloadThread

mythread = DownloadThread(db, logging.getLogger('werkzeug'))
# mythread = Thread()
thread_status = 0


@app.route("/")
def main():
    return render_template('index.html', posts={1, 2, 3, 4, 5})


@app.route('/run', methods=['GET', 'POST'])
def run():
    global mythread, thread_status
    if thread_status == 0 or 2:
        mythread.start()
        thread_status = 1

    return('', 204)  # empty http response


@app.route("/settings", methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    reddit_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first()
    if not form.validate_on_submit():
        flash("Please enter keys for required services")
    return render_template('settings.html', form=form, reddit_token=reddit_token, readability_token=None,
                           evernote_token=None)


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
    reddit_db_entry = db.session.query(models.Settings).filter_by(setting_name='reddit_refresh_token').first()
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


@app.route('/thread')
def thread():
    t = Thread(target=tester)
    t.start()
    return 'ayy'


def tester():
    import time
    time.sleep(5)
    print("slept")


if __name__ == "__main__":
    app.run(debug=True)
