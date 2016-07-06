import json
import logging
from queue import Queue

import os
import praw
from Resources.forms import SettingsForm
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, send_file, jsonify, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

# import models so db knows where the models are
from Resources import models
from Resources.DownloadThread import DownloadThread

logger = logging.getLogger('werkzeug')
thread_status_queue = Queue()


@app.route("/")
def main():
    page = request.args.get('page')
    sort = request.args.get('sort')
    if page is not None and page is not 'None':
        page = int(page)
    else:
        page = 1
    posts = models.Post.query
    if sort == "date":
        posts = posts.order_by(models.Post.date_posted)
    elif sort == 'date_desc':
        posts = posts.order_by(desc(models.Post.date_posted))
    elif sort == "desc":
        posts = posts.order_by(models.Post.date_downloaded)
    else:
        posts = posts.order_by(desc(models.Post.date_downloaded))

    posts_per_page = int(settings_dict['number_of_posts'].setting_value)
    posts = posts.paginate(page, posts_per_page, False)
    return render_color_template('index.html', posts=posts)


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
        return render_color_template('post_text.html', title=post.title[0:64] + '...', post=post,
                                     comments=json.loads(post.comments))
    elif post.type == 'image' or post.type == 'album':
        # images = json.loads(post.body_content)
        return render_color_template('post_album.html', title=post.title[0:64] + '...',
                                     images=json.loads(post.body_content),
                                     post=post, comments=json.loads(post.comments))
    elif post.type == 'video':
        # images = json.loads(post.body_content)
        return render_color_template('post_video.html', title=post.title[0:64] + '...',
                                     videos=json.loads(post.body_content),
                                     post=post,
                                     comments=json.loads(post.comments))
    elif post.type == 'article':
        return render_color_template('post_text.html', title=post.title[0:64] + '...', post=post,
                                     comments=json.loads(post.comments))


@app.route('/delete_post')
def delete_post():
    code = request.args.get('post')
    return_json = {}
    post = db.session.query(models.Post).filter_by(code=code).first()
    if post.type == 'album' or post.type == 'image' or post.type == 'video':
        images = json.loads(post.body_content)
        for image in images:
            db_image = db.session.query(models.Images).filter_by(file_name=image['filename'])
            os.remove(db_image.first().file_path)
            db_image.delete()
        try:
            db.session.commit()
        except IntegrityError:
            print("Error removing image from database")  # Change to logger object when that gets integrated
            db.session.rollback()
    try:
        post.permalink = None
        post.title = None
        post.body_content = None
        post.date_posted = None
        post.author_id = None
        post.type = None
        post.summary = None
        db.session.commit()
        return_json["success"] = True
    except IntegrityError:
        db.session.rollback()
        return_json["success"] = False
    return jsonify(return_json)


@app.route('/user/<username>')
def user(username):
    username = models.Author.query.filter_by(username=username).first()
    posts = models.Post.query.filter_by(author=username)
    return render_color_template('user.html', user=username, posts=posts)


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
                mythread = DownloadThread(db, logger, thread_status_queue, settings_dict)
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
    except IntegrityError:
        db.session.rollback()
        response["status"] = "fail"
    return jsonify(response)


@app.route("/settings", methods=['GET', 'POST'])
def settings():
    global settings_dict
    form = SettingsForm()
    reddit_token = settings_dict['reddit_refresh_token']
    num_of_comments = settings_dict['number_of_comments']
    save_comments = settings_dict['save_comments']
    num_of_posts = settings_dict['number_of_posts']
    color = settings_dict['color']
    cron_string = settings_dict['cron_string'].setting_value
    if form.validate_on_submit():
        if form.number_of_comments.data != num_of_comments.setting_value:
            settings_dict['number_of_comments'].setting_value = form.number_of_comments.data
            db.session.query(models.Settings).filter_by(
                setting_name='number_of_comments').first().setting_value = form.number_of_comments.data

        if form.save_comments.data != save_comments.setting_value:
            settings_dict['save_comments'].setting_value = str(form.save_comments.data)
            db.session.query(models.Settings).filter_by(
                setting_name='save_comments').first().setting_value = str(form.save_comments.data)

        if form.number_of_posts.data != num_of_posts.setting_value:
            settings_dict['number_of_posts'].setting_value = form.number_of_posts.data
            db.session.query(models.Settings).filter_by(
                setting_name='number_of_posts').first().setting_value = form.number_of_posts.data

        if form.color.data != color.setting_value:
            settings_dict['color'].setting_value = form.color.data
            db.session.query(models.Settings).filter_by(setting_name='color').first().setting_value = form.color.data

        if form.cron_string.data != cron_string:
            settings_dict['cron_string'].setting_value = form.cron_string.data
            db.session.query(models.Settings).filter_by(
                setting_name='cron_string').first().setting_value = form.cron_string.data

        try:
            db.session.commit()
            logger.info("Settings updated")
            flash("Settings updated successfully")
        except IntegrityError as e:
            db.session.rollback()
            logger.error("Error updating settings - %s", e)

        # Update job schedule if data has changed since last write
        if form.cron_string.data != cron_string:
            global job
            cron_array = get_cron_array(settings_dict['cron_string'].setting_value)
            job.reschedule('cron', minute=cron_array[0], hour=cron_array[1], day=cron_array[2],
                           month=cron_array[3], day_of_week=cron_array[4])
            logger.info("Next job rescheduled to {}".format(settings_dict['cron_string'].setting_value))

        return redirect('/settings')
    else:
        flash_errors(form)

    # Set the values of the input boxes in the form
    form.color.data = color.setting_value
    return render_color_template('settings.html', form=form, reddit_token=reddit_token, evernote_token=None,
                                 num_of_comments=num_of_comments, save_comments=save_comments,
                                 num_of_posts=num_of_posts, cron_string=cron_string)


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (getattr(form, field).label.text, error), "error")


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
    return render_color_template('reddit_wizard.html', client_id=client_id, response_type=response_type, state=state,
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


def render_color_template(template, **kwargs):
    return render_template(template, color=settings_dict['color'].setting_value, **kwargs)


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


def get_cron_array(cron_string):
    """
    Create an array of strings representing the values for each field in the cron string. String split on space (' ')
    Fields are in order according to standard cron format:

    - Minute (0-59)
    - Hour (0-23)
    - Day of Month (1-31)
    - Month (0-12)
    - Weekday (0-6, Monday is 0)

    :param cron_string: Input cron string
    :type cron_string: str
    :return: Array of strings representing each field of cron string.
    :rtype: list
    """
    return cron_string.split(" ")


def set_schedule():
    """
    Set up the scheduler to run the download thread (via the run() function) at the time specified in the settings

    :return: The job created for the scheduler for the run() function.
    :rtype: apscheduler.job.Job
    """
    logger.info("Starting scheduler")
    scheduler = BackgroundScheduler()
    cron_array = get_cron_array(settings_dict['cron_string'].setting_value)
    cron_job = scheduler.add_job(run, 'cron', minute=cron_array[0], hour=cron_array[1], day=cron_array[2],
                                 month=cron_array[3], day_of_week=cron_array[4])
    scheduler.start()
    return cron_job


if __name__ == "__main__":
    settings_dict = {}
    for setting in models.Settings.query.all():
        settings_dict[setting.setting_name] = setting
    # Create a dict of settings so that the db doesn't have to be queried constantly.
    mythread = DownloadThread(db, logger, thread_status_queue, settings_dict)
    job = set_schedule()

    import first_run
    first_run.check_if_first_run()
    app.run(debug=False)
