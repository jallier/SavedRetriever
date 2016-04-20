import json
import logging
from queue import Queue

import praw
from flask import Flask, render_template, request, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc

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
    page = request.args.get('page')
    sort = request.args.get('sort')
    if page is not None and page is not 'None':
        page = int(page)
    else:
        page = 1
    posts = models.Post.query
    if sort == "desc":
        posts = posts.order_by(desc(models.Post.id))
    elif sort == "date":
        posts = posts.order_by(models.Post.date)
    elif sort == 'date_desc':
        posts = posts.order_by(desc(models.Post.date))
    posts = posts.paginate(page, 20, False)
    return render_template('index.html', posts=posts)


@app.route('/img/<filename>')
def show_image(filename):
    image = db.session.query(models.Images).filter_by(file_name=filename).first().file_path
    mime = image.split('.')[-1]
    if mime == 'mp4':
        mime = 'video/' + mime
    else:
        mime = 'image/' + mime
    return send_file(image, mimetype=mime)


@app.route('/post/<postid>')
def show_post(postid):
    post = models.Post.query.filter_by(code=postid).first()
    if post.type == 'text':
        return render_template('post_text.html', title=post.title[0:64] + '...', post=post, comments=json.loads(post.comments))
    elif post.type == 'image' or 'album' or 'video':
        return render_template('post_album.html', title=post.title[0:64] + '...', post=post, comments=json.loads(post.comments))
    elif post.type == 'article':
        return render_template('post_text.html', title=post.title[0:64] + '...', post=post, comments=json.loads(post.comments))


@app.route('/user/<username>')
def user(username):
    username = models.Author.query.filter_by(username=username).first()
    posts = models.Post.query.filter_by(author=username)
    return render_template('user.html', user=username, posts=posts)


@app.route('/status')
def thread_status():
    global mythread
    thread_state = get_thread_state()
    if thread_state == 1:
        count = mythread.get_number_items_downloaded()
        response = {
            'count': count,
            'status': 'running'
        }
    elif thread_state == 2:
        count = mythread.get_number_items_downloaded()
        response = {
            'count': count,
            'status': 'finished'
        }
    else:
        response = {
            'count': 0,
            'status': 'ready'
        }
        set_thread_status(0)
    # print(json.dumps(response))
    return jsonify(response)


def get_thread_state():
    global thread_status_queue
    thread_state = thread_status_queue.get()
    thread_status_queue.put(thread_state)
    return thread_state


def set_thread_status(status):
    global thread_status_queue
    thread_status_queue.get()
    thread_status_queue.put(status)


@app.route('/cancel', methods=['POST'])
def cancel():
    global mythread
    mythread.join()
    return '', 204


@app.route('/run', methods=['GET', 'POST'])
def run():
    global mythread
    if not mythread.is_alive():
        try:
            mythread.start()
        except RuntimeError as e:
            if e.args[0] == "threads can only be started once":  # Thread has already run; start a new one
                mythread = DownloadThread(db, logging.getLogger('werkzeug'), thread_status_queue)
                mythread.start()
            else:
                print(e)

    return '', 204  # empty http response


@app.route('/delete_all_posts', methods=['POST', 'GET'])
def delete_all_posts():
    response = {}
    try:
        db.session.query(models.Post).delete()
        db.session.query(models.Images).delete()
        db.session.commit()
        response["status"] = "success"
    except:
        db.session.rollback()
        response["status"] = "fail"
    return jsonify(response)


@app.route("/settings", methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    reddit_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first()
    # if not form.validate_on_submit():
    #     flash("Please enter keys for required services")
    return render_template('settings.html', form=form, reddit_token=reddit_token, evernote_token=None)


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
