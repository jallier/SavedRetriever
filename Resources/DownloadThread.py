import datetime
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from logging import handlers
from queue import Empty
from threading import Thread

import bleach
import imgurpython.helpers.error
import os
import praw
import re
import warnings
from Resources import models
from imgurpython import ImgurClient
from readability.readability import Document
from sqlalchemy.exc import IntegrityError, InterfaceError


class DownloadThread(Thread):
    def __init__(self, db, logger, output_queue, settings_dict):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        ch = logging.handlers.RotatingFileHandler("sr.log")
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.propagate = False

        self.db = db
        self.output_queue = output_queue
        self.stop_request = threading.Event()
        self.post_downloaded_count = 0
        self.settings_dict = settings_dict
        self.allowed_tags = [
            'a',
            'b',
            'br',
            'em',
            'h1',
            'h2',
            'h3',
            'h4',
            'h5',
            'h6',
            'img',
            'title',
            'p',
            'strong',
            'li',
            'ol',
            'ul',
            'table',
            'tr',
            'td',
            'blockquote',
            'caption',
            'strike',
            'big',
            'center',
            'cite',
            'code'
        ]

        self.allowed_attrs = {
            '*': ['href', 'src']
        }
        try:
            self.output_queue.get(timeout=0.1)
            self.output_queue.put(0)
        except Empty:
            self.output_queue.put(0)

    def run(self):
        """Start the download"""
        self.downloader()

    def image_saver(self, url, filename):
        """
        Saves an image to disk in the location specified

        :param url: url of the image to download
        :type url: string
        :param filename: path and filename of file to download
        :type filename: string
        :return: If image was downloaded successfully
        :rtype: bool
        """
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}
        request = urllib.request.Request(url, headers=header)
        try:
            with urllib.request.urlopen(request) as response, open(filename, "wb") as out_file:
                data = response.read()
                out_file.write(data)
        except urllib.error.HTTPError as e:
            self.logger.warning("Unable to save image: " + str(e))
            return False
        except OSError as e:
            self.logger.warning("Unable to save image: " + str(e))
            return False
        return True

    def subreddit_linker(self, input_text):
        """
        Fixes non-valid links to subreddits in text

        :param input_text: html string to fix
        :type input_text: str
        :return: fixed html str
        :rtype: str
        """
        pattern = 'href="/r/.*?"'
        matches = re.finditer(pattern, input_text)
        for i in matches:
            full_match = i.group()
            match = full_match.split('/')
            input_text = re.sub(full_match, 'href="http://www.reddit.com/r/{}'.format(match[-1]), input_text)
        return input_text

    def set_output_thread_condition(self, condition):
        """
        Sets the condition of the output thread

        - 0 = Ready to start
        - 1 = Running
        - 2 = Thread completed/stopped

        :param condition: Value of the condition
        :type condition: int
        :return: None
        """
        self.output_queue.get(False)
        self.output_queue.put(condition)

    def join(self, timeout=None):
        """
        Request the thread to stop

        :param timeout:
        :return:
        """
        self.stop_request.set()
        super(DownloadThread, self).join(timeout)

    def get_number_items_downloaded(self):
        """
        Get how many items have been downloaded by the thread

        :return: Amount of downloaded posts
        :rtype: int
        """
        return self.post_downloaded_count

    def _get_comments(self, submission, number_of_comments, r):
        """
        Get the top n comments (including author and score) from a given submission, and store them in the database
        in JSON format.

        :param submission: PRAW object of current submission
        :param number_of_comments: number of comments to download
        :type number_of_comments: int
        :param r: global PRAW object used to interface with reddit
        :return: JSON string of comments
        """
        if type(submission) == praw.objects.Comment:
            submission = r.get_submission(submission.permalink)
            comments = submission.comments[0].replies
        else:
            comments = submission.comments
        my_json = {}
        count = 0
        for comment in comments:
            if count > int(number_of_comments) - 1:  # Number of comments to grab
                break
            comment_id = 'comment_' + str(count)
            my_json[comment_id] = {'points': comment.score, 'child': {}}
            my_json[comment_id]['body'] = comment.body_html if comment.body_html is not None else 'deleted'
            my_json[comment_id]['author'] = comment.author.name if comment.author is not None else 'deleted'

            if len(comment.replies) != 0 and type(comment.replies[0]) is not praw.objects.MoreComments:
                my_json[comment_id]['child'] = {'points': comment.replies[0].score}
                my_json[comment_id]['child']['body'] = comment.replies[0].body_html if comment.replies[
                                                                                           0].body_html is not None else ''
                my_json[comment_id]['child']['author'] = comment.replies[0].author.name if comment.replies[
                                                                                               0].author is not None else 'deleted'
            count += 1
        return json.dumps(my_json)

    def _add_image_to_db(self, base_filename, filename):
        """
        Adds a downloaded image to the database to store the filepath of the image.

        :param base_filename: name of the file to be saved
        :type base_filename: str
        :param filename: file path of the file to be saved, relative to top level package
        :type filename: str
        :return: None
        """
        try:
            image = models.Images(file_name=base_filename, file_path=filename)
            self.db.session.add(image)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            self.logger.error(e)
            self.logger.error("Integrity error - Likely due to image already existing in the db")

    def _make_article_img_responsive(self, text):
        """
        Add img-responsive css class to img tags within html of articles to make them display better with bootstrap.

        :param text: html of article to be scanned
        :type text: str
        :return: scanned and fixed html string
        :rtype: str
        """
        capture = '<img[\s\S]+?>'
        sub = 'class=".*?"'
        cap = re.findall(capture, text)
        for i in cap:
            orig = i
            if re.search(sub, i) is None:
                i = i.replace('>', 'class="img-responsive">')
            else:
                i = re.sub(sub, 'class="img-responsive', i)
            text = re.sub(orig, i, text)
        return text

    def _get_image_url_type(self, url):
        """
        | Get the file extention of the url
        | eg .png, .jpg etc

        :param url: url to be checked for extention
        :type url: str
        :return: extention of the url
        :rtype: str
        """
        return re.sub("([^A-z0-9])\w+", "", url.split('.')[-1])

    def downloader(self):
        """
        Main download method. Gets index of saved posts from reddit using PRAW, then checks them against the posts
        already saved in the database. Posts will be downloaded and saved according to type of post (selfpost, image,
        image album, webm, article.)

        :return: None
        """
        self.set_output_thread_condition(1)
        self.stop_request.clear()
        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        logger = self.logger

        logger.info("\n###########\nStarting SR\n###########")

        logger.debug("Getting settings from db")
        get_comments = self.settings_dict['save_comments'].value
        number_of_comments = self.settings_dict['number_of_comments'].value

        path = "static/SRDownloads"
        if not os.path.exists(path):
            os.makedirs(path)

        # Authenticate with Reddit
        logger.info('Authenticating with Reddit')
        client_id = '_Nxh9h0Tys5KCQ'
        redirect_uri = 'http://127.0.0.1:5000/authorize_callback'
        refresh_token = self.settings_dict['reddit_refresh_token'].value
        user_agent = "SavedRetriever 0.9 by /u/fuzzycut"

        try:
            r = praw.Reddit(user_agent)
            r.set_oauth_app_info(client_id, '', redirect_uri)
            access_information = r.refresh_access_information(refresh_token)
            r.set_access_credentials(**access_information)
            logger.info("Authenticated")
        except Exception as e:
            logger.error(e)
            self.set_output_thread_condition(2)
            raise SystemExit
        time_since_accesstoken = time.time()

        index = set()
        try:  # Create index of unique post codes
            for post in models.Post.query.all():
                index.add(post.code)
        except OSError:
            logger.error("Unable to create index")
            raise SystemExit

        logger.info("Beginning to save files to db...")
        items = r.get_me().get_saved(limit=None)
        self.post_downloaded_count = 0
        # Convert saved post generator to a list in order to iterate backwards, so that the most recent saved post
        # is the most recently downloaded
        for i in list(items)[::-1]:
            if self.stop_request.is_set():
                logger.info('Cancelling download...')
                break

            if (time.time() - time_since_accesstoken) / 60 > 55:  # Refresh the access token before it runs out.
                logger.debug('Refreshing Reddit token')
                r.refresh_access_information(access_information['refresh_token'])
                time_since_accesstoken = time.time()

            name = i.name

            if name not in index:  # file has not been downloaded
                permalink = i.permalink
                title = i.link_title if hasattr(i, 'link_title') else i.title
                date = datetime.datetime.fromtimestamp(i.created)
                post = None
                author = str(i.author)
                user = models.Author.query.filter_by(username=author)
                logger.info('Getting post ' + name + ' - ' + title[:255])
                if user.count() == 0:  # user is not in db
                    user = models.Author(username=author)
                    self.db.session.add(user)
                    self.db.session.commit()
                else:
                    user = user.first()
                comments = self._get_comments(i, number_of_comments, r) if get_comments == 'True' else "{}"
                # ========== #
                # IS COMMENT #
                # ========== #
                if hasattr(i, 'body_html'):
                    logger.debug("{} is comment".format(name))
                    body = i.body_html

                    # html output
                    body = self.subreddit_linker(body)
                    summary = body[:600]
                    summary = bleach.clean(summary, tags=self.allowed_tags, attributes=self.allowed_attrs, strip=True)
                    post = models.Post(permalink=permalink, title=title, body_content=body, date_posted=date,
                                       author_id=user.id, code=name, type='text', summary=summary, comments=comments)

                # ============ #
                # IS SELF-POST #
                # ============ #
                elif hasattr(i, 'is_self') and i.is_self is True:
                    logger.debug('{} is self-post'.format(name))
                    text = i.selftext_html if i.selftext_html is not None else ""

                    # html output
                    text = self.subreddit_linker(text)
                    summary = text[:600]
                    summary = bleach.clean(summary, tags=self.allowed_tags, attributes=self.allowed_attrs, strip=True)
                    post = models.Post(permalink=permalink, title=title, body_content=text, date_posted=date,
                                       author_id=user.id, code=name, type='text', summary=summary,
                                       comments=comments)

                # ====================== #
                # IS DIRECT LINKED IMAGE #
                # ====================== #
                elif (hasattr(i, 'url') and (self._get_image_url_type(i.url) in ['jpg', 'png', 'gif', 'gifv', 'pdf'])
                      or "reddituploads" in i.url):
                    logger.debug('{} is direct linked image'.format(name))
                    url = i.url
                    base_filename = "{}_image.{}".format(name, self._get_image_url_type(url))
                    filename = path + "/" + base_filename
                    filetype = 'image'

                    if url[-4:] == "gifv":
                        url = url.replace('gifv', 'mp4')
                        filename = filename.replace('gifv', 'mp4')
                        base_filename = base_filename.replace('gifv', 'mp4')
                        base_filename = base_filename.replace('_image', '_video')
                        filetype = 'video'

                    # image downloader section
                    if os.path.exists(filename) and (os.path.getsize(filename) > 0):  # If image exists and is valid
                        image_downloaded = True
                        logger.info("Image already exists - {}".format(base_filename))
                    else:
                        image_downloaded = self.image_saver(url, filename)

                    if image_downloaded:
                        logger.info('Downloaded image - {}'.format(base_filename))
                        self._add_image_to_db(base_filename, filename)

                        if filename.split('.')[-1] == 'pdf':
                            img = '<a href="static/SRDownloads/{}">Click here for link to downloaded pdf</a>'.format(
                                base_filename)
                        elif filename.split('.')[-1] == 'mp4':
                            img = '<video class="sr-image img-responsive" id="share-video" autoplay="" muted=""' \
                                  ' loop=""><source id="mp4Source" src="/img/{}" type=' \
                                  '"video/mp4">Sorry,' \
                                  ' your browser doesn\'t support HTML5 video.  </video>'.format(base_filename)
                        else:
                            img = '<a href="/img/{0}"><img class="sr-image img-responsive" src="/img/{0}">' \
                                  '</a>'.format(base_filename)
                    else:
                        img = "Image failed to download - It may be temporarily or permanently unavailable"

                    img_json = [{"name": "", "filename": base_filename, "description": ""}]
                    img_json = json.dumps(img_json)
                    post = models.Post(permalink=permalink, title=title, body_content=img_json, date_posted=date,
                                       author_id=user.id, code=name, type=filetype, summary=img,
                                       comments=comments)

                # =============== #
                # IS GFYCAT IMAGE #
                # =============== #
                elif hasattr(i, 'url') and 'gfycat.com' in i.url:
                    json_url = 'https://gfycat.com/cajax/get/'
                    gfy_id = i.url.split('/')[-1]
                    url = json_url + gfy_id
                    data = None
                    try:
                        with urllib.request.urlopen(url) as response:
                            data = response.read().decode('utf-8')
                    except urllib.error.HTTPError:
                        logger.warn("Unable to open gfycat url" + url)

                    json_data = json.loads(data)
                    base_filename = "{}_video.{}".format(name, 'mp4')  # filename for image. regex same as above.
                    filename = path + "/" + base_filename
                    if os.path.exists(filename) and (os.path.getsize(filename) > 0):  # If image exists and is valid
                        image_downloaded = True
                        logger.info("Image already exists - {}".format(base_filename))
                    else:
                        image_downloaded = self.image_saver(json_data['gfyItem']['mp4Url'], filename)

                    if image_downloaded:
                        logger.info('Downloaded video - {}'.format(base_filename))
                        self._add_image_to_db(base_filename, filename)

                        img = '<video class="sr-image img-responsive" id="share-video" autoplay="" muted="" loop="">' \
                              '<source id="mp4Source" src="/img/{}" type="video/mp4">Sorry, your browser doesn\'t support ' \
                              'HTML5 video.  </video>'.format(base_filename)
                    else:
                        img = "Image failed to download - It may be temporarily or permanently unavailable"

                    img_json = [{"name": "", "filename": base_filename, "description": ""}]
                    img_json = json.dumps(img_json)
                    post = models.Post(permalink=permalink, title=title, body_content=img_json, date_posted=date,
                                       author_id=user.id, code=name, type='video', summary=img,
                                       comments=comments)

                # ============== #
                # IS IMGUR ALBUM #
                # ============== #
                elif hasattr(i, 'url') and 'imgur' in i.url:  # Add option to download images to folder.
                    logger.debug('{} is Imgur album'.format(name))
                    url = i.url
                    # body = "<h2>{}</h2>".format(title)
                    body = []
                    summary = ''

                    # imgur api section
                    client = ImgurClient('755357eb4cd70bd', None)
                    pattern = '\/([A-z0-9]{5,7})'  # matches any 5-7 long word that comes after a forward slash (/).
                    match = re.findall(pattern, url)
                    gallery_id = match[-1].replace('/', '')  # removes any forward slashes for processing
                    gallery = []
                    filename = None
                    try:
                        gallery = client.get_album_images(gallery_id)
                    except imgurpython.helpers.error.ImgurClientError:  # if 'gallery' is actually just a lone image
                        try:
                            gallery = [client.get_image(gallery_id)]
                        except imgurpython.helpers.error.ImgurClientError as error:  # if gallery does not exist.
                            if error.status_code != 404:
                                logger.error("**{} - {}**".format(error.status_code, error.error_message))
                            else:
                                logger.error(error)

                    img_path = path

                    first_image = True
                    for image in gallery:  # add if gallery > 10, then just add a link (would be too large for the note)
                        image_name = image.title if image.title is not None else ""
                        # image_description = image.description if image.description is not None else ""
                        if image.description != title and image.description is not None:
                            image_description = image.description
                        else:
                            image_description = ""
                        image_filetype = image.type.split('/')[1]
                        image_id = image.id
                        image_link = image.link
                        # sets up downloaded filename and html for embedding image
                        base_filename = "{}_image.{}".format(image_id, image_filetype)
                        img_json = [{"name": image_name, "filename": base_filename, "description": image_description}]
                        filename = img_path + "/" + base_filename
                        # only download if file doesn't already exist
                        if os.path.exists(filename) and (os.path.getsize(filename) > 0):
                            image_downloaded = True
                            logger.info('Image already exists - {}'.format(base_filename))
                        else:
                            image_downloaded = self.image_saver(image_link, filename)

                        if image_downloaded:
                            logger.info('Image downloaded - {}'.format(base_filename))
                            self._add_image_to_db(base_filename, filename)

                        if first_image:
                            summary = '<a href="/img/{0}"><img src="/img/{0}"' \
                                      ' class="sr-image img-responsive"></a>'.format(base_filename)
                            first_image = False

                        body += img_json

                    post = models.Post(permalink=permalink, title=title + " - Album", body_content=json.dumps(body),
                                       date_posted=date, author_id=user.id, code=name, type='album', summary=summary,
                                       comments=comments)

                # ========== #
                # IS ARTICLE #
                # ========== #
                elif hasattr(i, 'title') and i.is_self is False:
                    logger.debug('{} is article/webpage'.format(name))
                    url = i.url
                    html = None
                    try:
                        # Set header to trick some sites into letting the script pull the article
                        header = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) '
                                                'Gecko/2009021910 Firefox/3.0.7'}
                        request = urllib.request.Request(url, headers=header)
                        with urllib.request.urlopen(request) as response:
                            html = response.read()
                    except urllib.error.HTTPError as e:
                        self.logger.error("Unable to access article url\n %s\n %s\n %s", e, url, i.name)
                        continue
                    except urllib.error.URLError as e:
                        self.logger.error("Unable to access article url\n %s\n %s\n %s", e, url, i.name)
                        continue

                    article = Document(html)
                    article_text = article.summary()
                    article_text = bleach.clean(article_text, tags=self.allowed_tags, attributes=self.allowed_attrs,
                                                strip=True)
                    summary = article_text[:600]
                    summary = bleach.clean(summary, tags=self.allowed_tags, attributes=self.allowed_attrs, strip=True)
                    article_text = self._make_article_img_responsive(article_text)
                    article_text = '<a href="{}">Original article</a>'.format(url) + article_text

                    if article_text is None:  # if unable to parse document, manually set an error message
                        article_text = 'Unable to parse page - See <a href="{}">here</a> for the original link'.format(
                            url)
                    # article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article

                    post = models.Post(permalink=permalink, title=title, body_content=article_text, date_posted=date,
                                       author_id=user.id, code=name, type='article', summary=summary,
                                       comments=comments)

                # end of checking for saved items #
                try:
                    self.db.session.add(post)
                    self.db.session.commit()
                except InterfaceError:
                    self.db.session.rollback()
                    self.logger.error("Error adding post to db - {}".format(post.title))
                    continue
                self.post_downloaded_count += 1
                logger.info('Saved ' + name + ' - ' + title[:255])

        # end of for loop
        logger.info("All items downloaded")
        self.set_output_thread_condition(2)
