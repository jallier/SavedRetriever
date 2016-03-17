import datetime
import logging
import warnings
# import json
# import urllib.request
import os
# import argparse
import re
# import urllib.error
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
    def __init__(self, db, logger):
        Thread.__init__(self)
        self.db = db
        self.logger = logger

    def run(self):
        self.downloader()

    def read_command_args(self):
        pass

    def create_logger(self, log_to_console=True):
        return self.logger
        # return CommonUtils.Utils.create_logger(log_to_console)


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

    def downloader(self):
        # if not os.path.isfile('credentials.config'):  # if credentials file does not exist, start the first run function
            #first_run()  # Authenticate and generate the credentials file.

        # command line switches function
        # args = self.read_command_args()
        # use_evernote = args.e
        # debug_mode = args.debug
        # delete_files = args.t if use_evernote is True else False
        # path = args.p
        # info_mode = args.i
        #
        # if debug_mode:
        #     logger = create_logger(log_to_console=True)
        #     logger.setLevel(logging.DEBUG)
        #     logger.info('Warning - Debug mode active. Files will be downloaded, but not added to index')
        # elif info_mode:
        #     warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        #     logger = create_logger(log_to_console=True)
        # else:
        #     warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        #     logger = create_logger()

        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        logger = self.create_logger(log_to_console=True)

        logger.info("\n###########\nStarting SR\n###########")

        # Create the downloads folder on the specified path, or in the dir where file is stored.
        # if path is not "":
        #     path = path[0]
        # else:
        path = os.getcwd()
        path += "/SRDownloads"

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

        # if use_evernote is True:
        #     enclient = evernoteWrapper.Client(credentials['evernote']['dev_token'], 'Saved from Reddit')

        # html_index_file = None
        # if delete_files is False:  # only create index if we're going to use it.
        #     html_index_file = html_index.index(r.get_me().name, path)

        # try:
        #     ind = open('index.txt', 'a')  # open index file for appending
        # except OSError:
        #     logger.error("Unable to open index file for writing")
        #     raise SystemExit

        logger.info("Beginning to save files to db...")
        for i in r.get_me().get_saved(limit=1):
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
                title = i.link_title if hasattr(i, 'link_title') else i.title
                # ========== #
                # IS COMMENT #
                # ========== #
                if hasattr(i, 'body_html'):
                    logger.debug("{} is comment".format(name))
                    body = i.body_html
                    date = datetime.datetime.fromtimestamp(i.created)

                    # html output
                    body = self.subreddit_linker(body)
                    # output = html_output_string(permalink, author, body, title)

                    user = models.Author.query.filter_by(username=author)
                    if len(list(user)) == 0:  # user is not in db
                        user = models.Author(username=author)
                        self.db.session.add(user)
                        self.db.session.commit()
                    else:
                        user = user.first()
                    post = models.Post(permalink=permalink, title=title, body_content=body, date=date, author_id=user.id, code=name)
                    self.db.session.add(post)
                    self.db.session.commit()

                    # if delete_files is False:
                    #     file_name = html_writer(path, name, output)

                    # en api section
                    # if use_evernote is True:
                    #     enclient.new_note(title)
                    #     enclient.add_html(output)
                    #     enclient.add_tag(*evernote_tags)  # the * is very important. It unpacks the tags tuple properly
                    #     note = enclient.create_note()
                # ============ #
                # IS SELF-POST #
                # ============ #
                # elif hasattr(i, 'is_self') and i.is_self is True:
                #     logger.debug('{} is self-post'.format(name))
                #     text = i.selftext_html if i.selftext_html is not None else ""
                #
                #     # html output
                #     text = self.subreddit_linker(text)
                #     output = html_output_string(permalink, author, text, title)
                #     if delete_files is False:
                #         file_name = html_writer(path, name, output)
                #
                #     # en api section
                #     if use_evernote is True:
                #         enclient.new_note(title)
                #         enclient.add_tag(*evernote_tags)
                #         enclient.add_html(output)
                #         note = enclient.create_note()
                # # ====================== #
                # # IS DIRECT LINKED IMAGE #
                # # ====================== #
                # elif hasattr(i, 'url') and re.sub("([^A-z0-9])\w+", "", i.url.split('.')[-1]) in ['jpg', 'png', 'gif', 'gifv', 'pdf']:
                #     """
                #     Need to check file types and test pdf. How does this handle gfycat and webm? Can EN display that inline?
                #     The regex in the if is to strip out non-valid filetype chars.
                #     """
                #     logger.debug('{} is direct linked image'.format(name))
                #     url = i.url
                #     base_filename = "{}_image.{}".format(name, re.sub("([^A-z0-9])\w+", "", url.split('.')[
                #         -1]))  # filename for image. regex same as above.
                #     filename = path + "/" + base_filename
                #
                #     # image downloader section
                #     if os.path.exists(filename) and (os.path.getsize(filename) > 0):  # If image exists and is valid
                #         image_downloaded = True
                #         logger.info("Image already exists - {}".format(base_filename))
                #     else:
                #         image_downloaded = image_saver(url, filename)
                #         logger.info('Downloaded image - {}'.format(base_filename))
                #
                #     if image_downloaded:
                #         # write image as <img> or link to local pdf downloaded in html file
                #         if filename.split('.')[-1] == 'pdf':
                #             img = '<a href="{}">Click here for link to downloaded pdf</a>'.format(base_filename)
                #         else:
                #             img = '<br><a href="{0}"><img src="{0}"></a>'.format(
                #                 base_filename)  # html for embedding in html file
                #     else:
                #         img = "Image failed to download - It may be temporarily or permanently unavailable"
                #
                #     # Evernote api section
                #     if use_evernote is True:
                #         enclient.new_note(title)
                #         enclient.add_tag(*evernote_tags)
                #         enclient.add_html(html_output_string_image(permalink, author, "", title))  # should add body="" in the function
                #         if image_downloaded:
                #             enclient.add_resource(filename)
                #         note = enclient.create_note()
                #
                #     if delete_files is False:
                #         file_name = html_writer(path, name, html_output_string_image(permalink, author, img, title))
                #     else:
                #         os.remove(filename)
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
        # if delete_files is False:
        #     html_index_file.save_and_close()
        # else:  # try remove downloads if -t is set, but don't force it if directory has things in it already.
        #     try:
        #         os.rmdir('Downloads')
        #     except OSError:
        #         logger.error("Unable to remove files")