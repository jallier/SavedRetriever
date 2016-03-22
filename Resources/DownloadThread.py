import datetime
import json
import logging
import warnings
# import json
import urllib.request
import os
# import argparse
import re
import urllib.error
# import shutil
import praw
# import imgurpython.helpers.error
import time
from time import strftime
from logging.handlers import RotatingFileHandler
# from readability.readability import Document
# from imgurpython import ImgurClient
# from Resources import evernoteWrapper
# from Resources import firstrun
# from Resources import html_index
from threading import Thread
from Resources import models
from Resources import CommonUtils


class DownloadThread(Thread):
    def __init__(self, db, logger, output_queue):
        Thread.__init__(self)
        self.db = db
        self.logger = logger
        self.output_queue = output_queue
        self.output_queue.put(0)

    def run(self):
        self.downloader()

    def create_logger(self):
        return self.logger

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
        logger = self.create_logger()

        logger.info("\n###########\nStarting SR\n###########")

        # path = os.getcwd()
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
        for i in r.get_me().get_saved(limit=2):
            if (time.time() - time_since_accesstoken) / 60 > 55:  # Refresh the access token before it runs out.
                logger.debug('Refreshing Reddit token')
                r.refresh_access_information(access_information['refresh_token'])
                time_since_accesstoken = time.time()

            name = i.name
            file_name = name  # to stop ide complaining.
            note = None
            evernote_tags = ('Reddit', 'SavedRetriever', '/r/' + i.subreddit.display_name)  # add config for this later

            # logger.info('Saving post - {}'.format(name))

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
                # ========== #
                # IS COMMENT #
                # ========== #
                if hasattr(i, 'body_html'):
                    logger.debug("{} is comment".format(name))
                    body = i.body_html
                    # date = datetime.datetime.fromtimestamp(i.created)

                    # html output
                    body = self.subreddit_linker(body)
                    # output = html_output_string(permalink, author, body, title)

                    post = models.Post(permalink=permalink, title=title, body_content=body, date=date,
                                       author_id=user.id, code=name)
                    self.db.session.add(post)
                    self.db.session.commit()

                # ============ #
                # IS SELF-POST #
                # ============ #
                elif hasattr(i, 'is_self') and i.is_self is True:
                    logger.debug('{} is self-post'.format(name))
                    text = i.selftext_html if i.selftext_html is not None else ""

                    # html output
                    text = self.subreddit_linker(text)
                    # output = html_output_string(permalink, author, text, title)

                    post = models.Post(permalink=permalink, title=title, body_content=text, date=date,
                                       author_id=user.id, code=name)
                    self.db.session.add(post)
                    self.db.session.commit()

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

                        # This should be rewritten to actually use the db
                        if filename.split('.')[-1] == 'pdf':
                            img = '<a href="static/SRDownloads/{}">Click here for link to downloaded pdf</a>'.format(
                                base_filename)
                        else:
                            img = '<a href="img/{0}"><img class="sr-image" src="img/{0}">' \
                                  '</a>'.format(base_filename)

                    else:
                        img = "Image failed to download - It may be temporarily or permanently unavailable"

                    post = models.Post(permalink=permalink, title=title, body_content=img, date=date,
                                       author_id=user.id, code=name)
                    self.db.session.add(post)
                    self.db.session.commit()

                # =============== #
                # IS GFYCAT IMAGE #
                # =============== #
                elif hasattr(i, 'url') and 'gfycat.com' in i.url:
                    json_url = 'https://gfycat.com/cajax/get/'
                    id = i.url.split('/')[-1]
                    url = json_url + id
                    data = None
                    from pprint import pprint
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

                        # This should be rewritten to actually use the db
                        img = '<video class="sr-image" id="share-video" autoplay="" muted="" loop="">' \
                              '<source id="mp4Source" src="img/{}" type="video/mp4">Sorry, your browser doesn\'t support ' \
                              'HTML5 video.  </video>'.format(base_filename)
                    else:
                        img = "Image failed to download - It may be temporarily or permanently unavailable"

                    post = models.Post(permalink=permalink, title=title, body_content=img, date=date,
                                       author_id=user.id, code=name)
                    self.db.session.add(post)
                    self.db.session.commit()
                    # pprint(json_data)

                # # ============== #
                # # IS IMGUR ALBUM #
                # # ============== #
                # elif hasattr(i, 'url') and 'imgur' in i.url:  # Add option to download images to folder.
                #     logger.debug('{} is Imgur album'.format(name))
                #     url = i.url
                #     body = "<h2>{}</h2>".format(title)
                #
                #     # imgur api section
                #     client = ImgurClient(credentials['imgur']['client_id'], credentials['imgur']['client_secret'])
                #     pattern = '\/([A-z0-9]{5,7})'  # matches any 5-7 long word that comes after a forward slash (/).
                #     match = re.findall(pattern, url)
                #     gallery_id = match[-1].replace('/', '')  # removes any forward slashes for processing
                #     gallery = []
                #     filename = None
                #     try:
                #         gallery = client.get_album_images(gallery_id)
                #     except imgurpython.helpers.error.ImgurClientError:  # if 'gallery' is actually just a lone image
                #         try:
                #             gallery = [client.get_image(gallery_id)]
                #         except imgurpython.helpers.error.ImgurClientError as error:  # if gallery does not exist. Is this the best way to do this?
                #             if debug_mode is True or error.status_code != 404:
                #                 print("**{} - {}**".format(error.status_code, error.error_message))
                #
                #     # img_path = 'Downloads/{}'.format(gallery_id)
                #     img_path = path + "/" + gallery_id
                #     if not os.path.exists(img_path):
                #         os.makedirs(img_path)
                #     for image in gallery:  # add if gallery > 10, then just add a link (would be too large for the note)
                #         image_name = image.title if image.title is not None else ""
                #         image_description = image.description if image.description is not None else ""
                #         image_filetype = image.type.split('/')[1]
                #         image_id = image.id
                #         image_link = image.link
                #         # sets up downloaded filename and html for embedding image
                #         base_filename = "{}_image.{}".format(image_id, image_filetype)
                #         img = '<p><h3>{0}</h3><a href="{1}/{2}"><img src="{1}/{2}"></a><br/>{3}</p>'.format(image_name,
                #                                                                                             gallery_id,
                #                                                                                             base_filename,
                #                                                                                             image_description)
                #         filename = img_path + "/" + base_filename
                #         if os.path.exists(filename) and (os.path.getsize(filename) > 0):  # only download if file doesn't already exist
                #             logger.info('Image already exists - {}'.format(base_filename))
                #         else:
                #             image_saver(image_link, filename)
                #             logger.info('Image downloaded - {}'.format(base_filename))
                #         body += img
                #
                #     # Evernote api section
                #     if use_evernote is True:
                #         enclient.new_note(title)
                #         enclient.add_tag(*evernote_tags)
                #         if len(gallery) == 1 and filename is not None:
                #             enclient.add_html(html_output_string_image(permalink, author, "", title))
                #             enclient.add_resource(filename)
                #         else:
                #             enclient.add_html(html_output_string_image(permalink, author,
                #             'This album is too large to embed; please see <a href="{}">here</a> for the original link.'.format(url),
                #                                                  title))
                #         note = enclient.create_note()
                #
                #     if delete_files is False:
                #         file_name = html_writer(path, name, html_output_string_image(permalink, author, body, title))
                #     else:
                #         shutil.rmtree(img_path)
                # # ========== #
                # # IS ARTICLE #
                # # ========== #
                # elif hasattr(i, 'title') and i.is_self is False:
                #     # This section needs work. It is semi-complete. Ultimately, adding in the full article is the goal.
                #     logger.debug('{} is article/webpage'.format(name))
                #     url = i.url
                #
                #     # readability api section
                #     parse_response = parse.get_article(url)
                #     article = parse_response.json()
                #     if 'content' not in article:  # if unable to parse document, manually set an error message
                #         article['content'] = 'Unable to parse page - See <a href="{}">here</a> for the original link'.format(url)
                #     article = article['content']
                #     article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article
                #
                #     # html output section.
                #     output = html_output_string(permalink, author, article, title)
                #     if delete_files is False:
                #         file_name = html_writer(path, name, output)
                #
                #     # Evernote section
                #     if use_evernote is True:
                #         enclient.new_note(title)
                #         enclient.add_tag(*evernote_tags)
                #         output = html_output_string(permalink, author, article, title)
                #         enclient.add_html(output)
                #
                #         # Add html file to note
                #         # enclient.add_resource("Downloads/{}.html".format(name))
                #         note = enclient.create_note()

                # end of checking for saved items #
                # failed_upload = False
                # if use_evernote is True:
                #     if note is not None:
                #         # print("Saved {:9} - GUID: {}".format(name, note.guid))
                #         logger.info('Saved {:9} - GUID: {}'.format(name, note.guid))
                #     else:  # Upload failed
                #         # print("Saved {:9} - Note failed to upload".format(name))
                #         logger.info('Saved {:9} - Note failed to upload'.format(name))
                #         failed_upload = True
                # elif use_evernote is False:
                logger.info('Saved ' + name)
                # if not debug_mode and not failed_upload:
                #     ind.write(name + "\n")
                #     ind.flush()  # this fixes python not writing the file if it terminates before .close() can be called
                #     if delete_files is False:
                #         html_index_file.add_link(title, file_name, permalink)

        # end of for loop
        # ind.close()
        logger.info("All items downloaded")
        self.set_output_thread_condition(2)
        # if delete_files is False:
        #     html_index_file.save_and_close()
        # else:  # try remove downloads if -t is set, but don't force it if directory has things in it already.
        #     try:
        #         os.rmdir('Downloads')
        #     except OSError:
        #         logger.error("Unable to remove files")
