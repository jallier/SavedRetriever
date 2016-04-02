import datetime
import json
import warnings
import urllib.request
import os
import re
import urllib.error
import praw
import imgurpython.helpers.error
import time
from imgurpython import ImgurClient
from threading import Thread
from readability.readability import Document

from Resources import models


class DownloadThread(Thread):
    def __init__(self, db, logger, output_queue):
        Thread.__init__(self)
        self.db = db
        self.logger = logger
        self.output_queue = output_queue
        self.output_queue.put(0)

    def run(self):
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
        try:
            with urllib.request.urlopen(url) as response, open(filename, "wb") as out_file:
                data = response.read()
                out_file.write(data)
        except OSError:
            self.logger.warn("Unable to save image")
        except urllib.error.HTTPError:
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
        self.output_queue.get(False)
        self.output_queue.put(condition)

    def downloader(self):
        self.set_output_thread_condition(1)
        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        logger = self.logger

        logger.info("\n###########\nStarting SR\n###########")

        path = "static/SRDownloads"

        if not os.path.exists(path):
            os.makedirs(path)

        # Authenticate with Reddit
        logger.info('Authenticating with Reddit')
        client_id = '_Nxh9h0Tys5KCQ'
        redirect_uri = 'http://127.0.0.1:5000/authorize_callback'
        refresh_token = models.Settings.query.filter_by(setting_name='reddit_refresh_token').first().setting_value
        user_agent = "SavedRetriever 0.9 by /u/fuzzycut"

        try:
            r = praw.Reddit(user_agent)
            r.set_oauth_app_info(client_id, '', redirect_uri)
            access_information = r.refresh_access_information(refresh_token)
            r.set_access_credentials(**access_information)
            logger.info("Authenticated")
        except Exception as e:
            logger.error(e)
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
        for i in r.get_me().get_saved(limit=1):
            if (time.time() - time_since_accesstoken) / 60 > 55:  # Refresh the access token before it runs out.
                logger.debug('Refreshing Reddit token')
                r.refresh_access_information(access_information['refresh_token'])
                time_since_accesstoken = time.time()

            name = i.name

            if name not in index:  # file has not been downloaded
                permalink = i.permalink
                author = str(i.author)
                user = models.Author.query.filter_by(username=author)
                if user.count() == 0:  # user is not in db
                    user = models.Author(username=author)
                    self.db.session.add(user)
                    self.db.session.commit()
                else:
                    user = user.first()
                title = i.link_title if hasattr(i, 'link_title') else i.title
                date = datetime.datetime.fromtimestamp(i.created)
                post = None
                # ========== #
                # IS COMMENT #
                # ========== #
                if hasattr(i, 'body_html'):
                    logger.debug("{} is comment".format(name))
                    body = i.body_html

                    # html output
                    body = self.subreddit_linker(body)
                    post = models.Post(permalink=permalink, title=title, body_content=body, date=date,
                                       author_id=user.id, code=name, type='text')

                # ============ #
                # IS SELF-POST #
                # ============ #
                elif hasattr(i, 'is_self') and i.is_self is True:
                    logger.debug('{} is self-post'.format(name))
                    text = i.selftext_html if i.selftext_html is not None else ""

                    # html output
                    text = self.subreddit_linker(text)
                    post = models.Post(permalink=permalink, title=title, body_content=text, date=date,
                                       author_id=user.id, code=name, type='text')

                # ====================== #
                # IS DIRECT LINKED IMAGE #
                # ====================== #
                elif hasattr(i, 'url') and re.sub("([^A-z0-9])\w+", "", i.url.split('.')[-1]) in ['jpg', 'png', 'gif',
                                                                                                  'gifv', 'pdf']:
                    logger.debug('{} is direct linked image'.format(name))
                    url = i.url
                    base_filename = "{}_image.{}".format(name, re.sub("([^A-z0-9])\w+", "", url.split('.')[
                        -1]))  # filename for image. regex same as above.
                    filename = path + "/" + base_filename
                    filetype = 'image'

                    if url[-4:] == "gifv":
                        url = url.replace('gifv', 'mp4')
                        filename = filename.replace('gifv', 'mp4')
                        base_filename = base_filename.replace('gifv', 'mp4')
                        filetype = 'video'

                    # image downloader section
                    if os.path.exists(filename) and (os.path.getsize(filename) > 0):  # If image exists and is valid
                        image_downloaded = True
                        logger.info("Image already exists - {}".format(base_filename))
                    else:
                        image_downloaded = self.image_saver(url, filename)

                    if image_downloaded:
                        logger.info('Downloaded image - {}'.format(base_filename))
                        image = models.Images(file_name=base_filename, file_path=filename)
                        self.db.session.add(image)
                        self.db.session.commit()

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

                    post = models.Post(permalink=permalink, title=title, body_content=img, date=date,
                                       author_id=user.id, code=name, type=filetype)

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
                        image = models.Images(file_name=base_filename, file_path=filename)
                        self.db.session.add(image)
                        self.db.session.commit()

                        img = '<video class="sr-image img-responsive" id="share-video" autoplay="" muted="" loop="">' \
                              '<source id="mp4Source" src="/img/{}" type="video/mp4">Sorry, your browser doesn\'t support ' \
                              'HTML5 video.  </video>'.format(base_filename)
                    else:
                        img = "Image failed to download - It may be temporarily or permanently unavailable"

                    post = models.Post(permalink=permalink, title=title, body_content=img, date=date,
                                       author_id=user.id, code=name, type='video')

                # ============== #
                # IS IMGUR ALBUM #
                # ============== #
                elif hasattr(i, 'url') and 'imgur' in i.url:  # Add option to download images to folder.
                    logger.debug('{} is Imgur album'.format(name))
                    url = i.url
                    body = "<h2>{}</h2>".format(title)

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
                        except imgurpython.helpers.error.ImgurClientError as error:  # if gallery does not exist. Is this the best way to do this?
                            if error.status_code != 404:
                                logger.error("**{} - {}**".format(error.status_code, error.error_message))
                            else:
                                logger.error(error)

                    img_path = path

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
                        img = '<div class="col-md-3"><h3>{0}</h3><a href="/img/{1}"><img src="/img/{1}"' \
                              ' class="sr-image img-responsive"></a><br/>{2}</div>'.format(image_name, base_filename,
                                                                                           image_description)
                        filename = img_path + "/" + base_filename
                        # only download if file doesn't already exist
                        if os.path.exists(filename) and (os.path.getsize(filename) > 0):
                            image_downloaded = True
                            logger.info('Image already exists - {}'.format(base_filename))
                        else:
                            image_downloaded = self.image_saver(image_link, filename)

                        if image_downloaded:
                            logger.info('Image downloaded - {}'.format(base_filename))
                            image = models.Images(file_name=base_filename, file_path=filename)
                            self.db.session.add(image)
                            self.db.session.commit()

                        body += img
                    post = models.Post(permalink=permalink, title=title, body_content=body, date=date,
                                       author_id=user.id, code=name, type='album')

                # ========== #
                # IS ARTICLE #
                # ========== #
                elif hasattr(i, 'title') and i.is_self is False:
                    logger.debug('{} is article/webpage'.format(name))
                    url = i.url
                    html = None
                    try:
                        with urllib.request.urlopen(url) as response:
                            html = response.read()
                    except OSError:
                        self.logger.warn("Unable to access article url")
                        break
                    except urllib.error.HTTPError:
                        self.logger.warn("Unable to access article url")
                        break

                    article = Document(html)
                    article_text = article.summary()

                    if article_text is None:  # if unable to parse document, manually set an error message
                        article_text = 'Unable to parse page - See <a href="{}">here</a> for the original link'.format(
                            url)
                    # article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article
                    post = models.Post(permalink=permalink, title=title, body_content=article_text, date=date,
                                       author_id=user.id, code=name, type='article')

                # end of checking for saved items #
                self.db.session.add(post)
                self.db.session.commit()
                logger.info('Saved ' + name)

        # end of for loop
        logger.info("All items downloaded")
        self.set_output_thread_condition(2)
