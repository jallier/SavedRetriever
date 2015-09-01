import logging
import warnings
import json
import urllib.request
import os
import argparse
import codecs
import re
import urllib.error
import shutil
import praw
import imgurpython.helpers.error
import time
from readability import ParserClient
from imgurpython import ImgurClient
from Resources import evernoteWrapper
from Resources import firstrun
from Resources import html_index

"""
Retreives saved content from reddit.
"""


def html_writer(path, file, output):
    """
    Writes an html file.
    :param path: Path to write file to
    :type path: str
    :param file: Name of the file to write
    :type file: str
    :param output: html content to write
    :type output: str
    :return: name of file written
    :rtype: str
    """
    name = file + ".html"
    file_name = "{}/{}".format(path, name)

    f = codecs.open(file_name, 'w', 'utf-8')
    # CSS styling for images. Does not affect text
    # html_image_size = "<head>\n<style>\nimg {max-width:100%;}\n</style>\n</head>\n"
    # f.write(html_image_size + output)
    f.write(output)
    f.close()
    return name


def html_output_string_image(permalink, author, body, title):
    """
    defines a global string to use to neaten up the output sections
    Returns a string of the html output for the items.
    """
    # '<a href="{0}">{0}</a><br/>by <a href="http://www.reddit.com/u/{1}">/u/{1}</a><br/><br/>{2}'.format(
    # permalink,
    # author,
    # body)

    output = '<head><style>\n' \
             'img {{max-width:100%;}}\n' \
             'html {{font-family:georgia;}}\n' \
             'h3 {{font-family:tahoma;}}\n' \
             '.main {{max-width:750px; margin-left:auto; margin-right:auto;}}\n' \
             '.right {{float:right;}}\n' \
             '</style>\n' \
             '<title>{title}</title></head>\n' \
             '<div><a href="{permalink}">Permalink</a>' \
             '<div style="display:inline;"> submitted by <a href="http://www.reddit.com/u/{author}">{author}</a>' \
             '</div>\n' \
             '<h3>{title}</h3><hr>\n' \
             '{body}'
    return output.format(permalink=permalink, author=author, title=title, body=body)


def html_output_string(permalink, author, body, title):
    output = '<head><style>\n' \
             'img {{max-width:100%;}}\n' \
             'html {{font-family:georgia;}}\n' \
             'h3 {{font-family:tahoma;}}\n' \
             '.main {{max-width:750px; margin-left:auto; margin-right:auto;}}\n' \
             '.right {{float:right;}}\n' \
             '</style>\n' \
             '<title>{title}</title></head>\n' \
             '<div class="main"><a href="{permalink}">Permalink</a>' \
             '<div style="display:inline;" class="right">submitted by <a href="http://www.reddit.com/u/{author}">{author}</a>' \
             '</div>\n' \
             '<h3>{title}</h3><hr>\n' \
             '{body}'
    return output.format(permalink=permalink, author=author, title=title, body=body)


def image_saver(url, filename):
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
    except urllib.error.HTTPError:
        return False
    return True


def read_command_args():
    """
    Reads commandline switches and returns an object containing the values of the switches
    :return:
    :rtype:
    """
    parser = argparse.ArgumentParser(description="Determine which services to use")
    parser.add_argument('-debug', action='store_true', default=False)  # debug mode on
    parser.add_argument('-e', '-evernote', action='store_true', default=False)  # use evernote
    parser.add_argument('-t', action='store_true', default=False)  # Temp mode. Delete html files after uploaded to evernote
    parser.add_argument('-p', '-path', nargs=1, default='')
    parser.add_argument('-i', action='store_true', default=False)  # Info mode. Will print out log to console.
    # add in an option for notebook name
    # add in an option for saving to index (independant from debugging)
    args = parser.parse_args()
    return args


def first_run():
    """
    Sets up credentials.config when the script is run for the first time.
    :return:
    :rtype:
    """
    reddit = firstrun.authenticate_reddit()
    evernote_dic = {"consumer_key": "your_key_here", "consumer_secret": "your_secret_here",
                    "dev_token": "Use this token"}
    imgur = {"client_id": "your_id_here", "client_secret": "your_secret_here"}
    readability = {"parser_key": "your_key_here"}

    dic = {'reddit': reddit, 'evernote': evernote_dic, 'imgur': imgur, 'readability': readability}

    with open('credentials.config', 'w') as f:
        f.write(json.dumps(dic, indent=2))

    print("\nAuthentication complete. To complete setup,"
          " fill in tokens for remaining services in credentials.config file")
    raise SystemExit


def create_logger(log_to_console=False):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_formatter = logging.Formatter("%(asctime)s: [%(name)s]: [%(levelname)s]: %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')

    file_handler = logging.FileHandler('SR.log')
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    if log_to_console is True:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    return logger


def main():
    # command line switches function
    args = read_command_args()
    use_evernote = args.e
    debug_mode = args.debug
    delete_files = args.t if use_evernote is True else False
    path = args.p
    info_mode = args.i

    if debug_mode:
        # print("Warning - Debug mode active. Files will be downloaded, but not added to index")
        logger = create_logger(log_to_console=True)
        logger.setLevel(logging.DEBUG)
        logger.info('Warning - Debug mode active. Files will be downloaded, but not added to index')
    elif info_mode:
        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        logger = create_logger(log_to_console=True)
    else:
        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.
        logger = create_logger()

    logger.info("\n###########\nStarting SR\n###########")

    if not os.path.isfile('credentials.config'):  # if credentials file does not exist, start the first run function
        first_run()  # Authenticate and generate the credentials file.

    with open('credentials.config', 'r') as json_file:
        credentials = json.load(json_file)  # get various OAuth tokens


    # Create the downloads folder on the specified path, or in the dir where file is stored.
    if path is not "":
        path = path[0]
    else:
        path = os.getcwd()
    path += "/SRDownloads"

    if not os.path.exists(path):
        os.makedirs(path)

    # Authenticate with Reddit
    logger.info('Authenticating with Reddit')
    client_id = credentials['reddit']['client_id']
    client_secret = credentials['reddit']['client_secret']
    redirect_uri = credentials['reddit']['redirect_uri']
    refresh_token = credentials['reddit']['refresh_token']
    user_agent = "SavedRetriever 0.9 by /u/fuzzycut"

    r = praw.Reddit(user_agent=user_agent,
                    oauth_client_id=client_id,
                    oauth_client_secret=client_secret,
                    oauth_redirect_uri=redirect_uri)

    access_information = r.refresh_access_information(refresh_token)
    r.set_access_credentials(**access_information)
    time_since_accesstoken = time.time()

    if os.path.isfile('index.txt'):  # checking for  index file, which contains index of downloaded files.
        with open('index.txt', 'r') as ind:
            index = ind.read()
        index = index.split()
    else:
        index = []

    if use_evernote is True:
        enclient = evernoteWrapper.Client(credentials['evernote']['dev_token'], 'Saved from Reddit')

    html_index_file = None
    if delete_files is False:  # only create index if we're going to use it.
        html_index_file = html_index.index(r.get_me().name, path)

    ind = open('index.txt', 'a')  # open index file for appending
    logger.info("Beginning to save files...")
    for i in r.get_me().get_saved(limit=None):
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
            author = i.author
            title = i.link_title if hasattr(i, 'link_title') else i.title
            # ========== #
            # IS COMMENT #
            # ========== #
            if hasattr(i, 'body_html'):
                logger.debug("Item is comment")
                body = i.body_html

                # html output
                output = html_output_string(permalink, author, body, title)
                if delete_files is False:
                    file_name = html_writer(path, name, output)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_html(output)
                    enclient.add_tag(*evernote_tags)  # the * is very important. It unpacks the tags tuple properly
                    note = enclient.create_note()
            # ============ #
            # IS SELF-POST #
            # ============ #
            elif hasattr(i, 'is_self') and i.is_self is True:
                logger.debug('Item is self-post')
                text = i.selftext_html

                # html output
                output = html_output_string(permalink, author, text, title)
                if delete_files is False:
                    file_name = html_writer(path, name, output)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_html(output)
                    note = enclient.create_note()
            # ====================== #
            # IS DIRECT LINKED IMAGE #
            # ====================== #
            elif hasattr(i, 'url') and re.sub("([^A-z0-9])\w+", "", i.url.split('.')[-1]) in ['jpg', 'png', 'gif', 'gifv', 'pdf']:
                """
                Need to check file types and test pdf. How does this handle gfycat and webm? Can EN display that inline?
                The regex in the if is to strip out non-valid filetype chars.
                """
                logger.debug('Item is direct linked image')
                url = i.url
                base_filename = "{}_image.{}".format(name, re.sub("([^A-z0-9])\w+", "", url.split('.')[
                    -1]))  # filename for image. regex same as above.
                filename = path + "/" + base_filename

                # image downloader section
                image_downloaded = image_saver(url, filename)
                logger.info('Downloaded image - {}'.format(base_filename))
                if image_downloaded:
                    # write image as <img> or link to local pdf downloaded in html file
                    if filename.split('.')[-1] == 'pdf':
                        img = '<a href="{}">Click here for link to downloaded pdf</a>'.format(base_filename)
                    else:
                        img = '<br><a href="{}"><img src="{}"></a>'.format(base_filename)  # html for embedding in html file
                else:
                    img = "Image failed to download - It may be temporarily or permanently unavailable"

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_text(html_output_string_image(permalink, author, "", title))  # should add body="" in the function
                    if image_downloaded:
                        enclient.add_resource(filename)
                    note = enclient.create_note()

                if delete_files is False:
                    file_name = html_writer(path, name, html_output_string_image(permalink, author, img, title))
                else:
                    os.remove(filename)
            # ============== #
            # IS IMGUR ALBUM #
            # ============== #
            elif hasattr(i, 'url') and 'imgur' in i.url:  # Add option to download images to folder.
                logger.debug('Item is Imgur album')
                url = i.url
                body = "<h2>{}</h2>".format(title)

                # imgur api section
                client = ImgurClient(credentials['imgur']['client_id'], credentials['imgur']['client_secret'])
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
                        if debug_mode is True or error.status_code != 404:
                            print("**{} - {}**".format(error.status_code, error.error_message))

                # img_path = 'Downloads/{}'.format(gallery_id)
                img_path = path + "/" + gallery_id
                if not os.path.exists(img_path):
                    os.makedirs(img_path)
                for image in gallery:  # add if gallery > 10, then just add a link (would be too large for the note)
                    image_name = image.title if image.title is not None else ""
                    image_description = image.description if image.description is not None else ""
                    image_filetype = image.type.split('/')[1]
                    image_id = image.id
                    image_link = image.link
                    # sets up downloaded filename and html for embedding image
                    base_filename = "{}_image.{}".format(image_id, image_filetype)
                    img = '<p><h3>{0}</h3><a href="{1}/{2}"><img src="{1}/{2}"></a><br/>{3}</p>'.format(image_name,
                                                                                                        gallery_id,
                                                                                                        base_filename,
                                                                                                        image_description)
                    filename = img_path + "/" + base_filename
                    if not os.path.exists(filename):  # only download if file doesn't already exist
                        image_saver(image_link, filename)
                        logger.info('Image downloaded - {}'.format(base_filename))
                    else:
                        logger.info('Image already exists - {}'.format(base_filename))
                    body += img

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    if len(gallery) == 1 and filename is not None:
                        enclient.add_html(html_output_string_image(permalink, author, "", title))
                        enclient.add_resource(filename)
                    else:
                        enclient.add_text(html_output_string_image(permalink, author,
                        'This album is too large to embed; please see <a href="{}">here</a> for the original link.'.format(url),
                                                             title))
                    note = enclient.create_note()

                if delete_files is False:
                    file_name = html_writer(path, name, html_output_string_image(permalink, author, body, title))
                else:
                    shutil.rmtree(img_path)
            # ========== #
            # IS ARTICLE #
            # ========== #
            elif hasattr(i, 'title') and i.is_self is False:
                # This section needs work. It is semi-complete. Ultimately, adding in the full article is the goal.
                logger.debug('Item is article/webpage')
                url = i.url

                # readability api section
                os.environ["READABILITY_PARSER_TOKEN"] = credentials['readability'][
                    'parser_key']  # set the environment variable as the parser key
                logger.info('Initializing Readability Client')
                parse = ParserClient()  # readability api doesn't take the token directly
                parse_response = parse.get_article(url)
                article = parse_response.json()
                if 'content' not in article:  # if unable to parse document, manually set an error message
                    article['content'] = 'Unable to parse page - See <a href="{}">here</a> for the original link'.format(url)
                article = article['content']
                article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article

                # html output section.
                output = html_output_string(permalink, author, article, title)
                if delete_files is False:
                    file_name = html_writer(path, name, output)

                # Evernote section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    output = html_output_string(permalink, author, article, title)
                    enclient.add_html(output)

                    # Add html file to note
                    # enclient.add_resource("Downloads/{}.html".format(name))
                    note = enclient.create_note()

            # end of checking for saved items #
            failed_upload = False
            if use_evernote is True:
                if note is not None:
                    # print("Saved {:9} - GUID: {}".format(name, note.guid))
                    logger.info('Saved {:9} - GUID: {}'.format(name, note.guid))
                else:  # Upload failed
                    # print("Saved {:9} - Note failed to upload".format(name))
                    logger.info('Saved {:9} - Note failed to upload'.format(name))
                    failed_upload = True
            elif use_evernote is False:
                # print("Saved " + name)
                logger.info('Saved ' + name)
            if not debug_mode and not failed_upload:
                ind.write(name + "\n")
                ind.flush()  # this fixes python not writing the file if it terminates before .close() can be called
                if delete_files is False:
                    html_index_file.add_link(title, file_name, permalink)

    # end of for loop
    ind.close()
    if delete_files is False:
        html_index_file.save_and_close()
    else:  # try remove downloads if -t is set, but don't force it if directory has things in it already.
        try:
            os.rmdir('Downloads')
        except OSError:
            pass

if __name__ == '__main__':
    with warnings.catch_warnings():  # This is to ignore ssl socket unclosed warnings.
        warnings.simplefilter('ignore')
        main()
