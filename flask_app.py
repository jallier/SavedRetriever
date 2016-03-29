import logging
from queue import Queue

import praw
from flask import Flask, render_template, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy

# import download as DownloadClient
from Resources.forms import SettingsForm

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

# import models so db knows where the models are
from Resources import models
from Resources.DownloadThread import DownloadThread

thread_status_queue = Queue()
mythread = DownloadThread(db, logging.getLogger('werkzeug'), thread_status_queue)


@app.route("/")
def main():
    posts = db.session.query(models.Post)
    return render_template('index.html', posts=posts)


@app.route('/img/<filename>')
def show_image(filename):
    # image = db.session.query(models.Images)
    image = models.Images.query.filter_by(file_name=filename).first().file_path
    return send_file(image)


@app.route('/post/<postid>')
def show_post(postid):
    post = models.Post.query.filter_by(code=postid).first()
    if post.type == 'text':
        return render_template('post_text.html', title=post.title[0:64] + '...', post=post)
    elif post.type == 'image':
        return render_template('post_image.html', title=post.title[0:64] + '...', post=post)
    elif post.type == 'album':
        return render_template('post_album.html', title=post.title[0:64] + '...', post=post)
    elif post.type == 'video':
        return render_template('post_image.html', title=post.title[0:64] + '...', post=post)
    elif post.type == 'article':
        return render_template('post_text.html', title=post.title[0:64] + '...', post=post)


@app.route('/run', methods=['GET', 'POST'])
def run():
    global mythread, thread_status, thread_status_queue
    thread_status = thread_status_queue.get()
    thread_status_queue.put(thread_status)
    if thread_status == 0:  # Thread is stopped
        mythread.start()
    elif thread_status == 1:
        pass
    elif thread_status == 2:  # Thread has run once; instantiate a new one
        mythread = DownloadThread(db, logging.getLogger('werkzeug'), thread_status_queue)
        mythread.start()

    return ('', 204)  # empty http response


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
    refresh_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first()
    if refresh_token is not None: refresh_token = refresh_token.setting_value
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


if __name__ == "__main__":
    app.run(debug=True)
