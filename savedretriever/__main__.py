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
from savedretriever.Resources import evernoteWrapper
from savedretriever.Resources import firstrun
from savedretriever.Resources import html_index

"""
Retreives saved content from reddit.

TODO:
    - Optimise code
    - Check EN if note exists?
    - Dropbox support?
    - Investigate using Goose to parse articles.
    - Fix the random ssl errors
    - Fix unicode errors
"""


def html_writer(file, output):
    """
    Writes an html file.

    Takes: the name of the file to write and the content (string) to write.
    Returns: the relative path of the downloaded file. (Relative to location of script)
    """
    file_name = "Downloads/{}.html".format(file)
    name = file + ".html"
    f = codecs.open(file_name, 'w', 'utf-8')
    # CSS styling for images. Does not affect text
    html_image_size = "<head>\n<style>\nimg {max-width:100%;}\n</style>\n</head>\n"
    f.write(html_image_size + output)
    f.close()
    return name


def html_output_string(permalink, author, body):
    """
    defines a global string to use to neaten up the output sections
    Returns a string of the html output for the items.
    """
    return '<a href="{0}">{0}</a><br/>by <a href="http://www.reddit.com/u/{1}">/u/{1}</a><br/><br/>{2}'.format(
        permalink,
        author,
        body)


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
                    "dev_token": "this can stay blank"}
    imgur = {"client_id": "your_id_here", "client_secret": "your_secret_here"}
    readability = {"parser_key": "your_key_here"}

    dic = {'reddit': reddit, 'evernote': evernote_dic, 'imgur': imgur, 'readability': readability}

    with open('credentials.config', 'w') as f:
        f.write(json.dumps(dic, indent=2))

    print("\nAuthentication complete. To complete setup,"
          " fill in tokens for remaining services in credentials.config file")
    raise SystemExit


def main():
    if not os.path.isfile('credentials.config'):  # if credentials file does not exist, start the first run function
        first_run()  # Authenticate and generate the credentials file.

    with open('credentials.config', 'r') as json_file:
        credentials = json.load(json_file)  # get various OAuth tokens

    # command line switches function
    args = read_command_args()
    use_evernote = args.e
    debug_mode = args.debug
    delete_files = args.t if use_evernote is True else False

    if debug_mode:
        print("Warning - Debug mode active. Files will be downloaded, but not added to index")
    else:
        warnings.warn("Suppressed Resource warning", ResourceWarning)  # suppresses sll unclosed socket warnings.

    # Authenticate with Reddit
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

    if not os.path.exists("Downloads"):
        os.makedirs("Downloads")

    if os.path.isfile('index.txt'):  # checking for  index file, which contains index of downloaded files.
        with open('index.txt', 'r') as ind:
            index = ind.read()
        index = index.split()
    else:
        index = []

    if use_evernote is True:
        enclient = evernoteWrapper.Client(credentials['evernote']['dev_token'], 'Saved from Reddit')

    if delete_files is False:  # only create index if we're going to use it.
        html_index_file = html_index.index(r.get_me().name)

    ind = open('index.txt', 'a')  # open index file for appending
    for i in r.get_me().get_saved(limit=None):
        if (time.time() - time_since_accesstoken) / 60 > 55:  # Refresh the access token before it runs out.
            r.refresh_access_information(access_information['refresh_token'])
            time_since_accesstoken = time.time()

        name = i.name
        file_name = name  # to stop ide complaining.
        note = None
        evernote_tags = ('Reddit', 'SavedRetriever', '/r/' + i.subreddit.display_name)  # add config for this later

        if name not in index:  # file has not been downloaded
            permalink = i.permalink
            author = i.author
            title = i.link_title if hasattr(i, 'link_title') else i.title

            if hasattr(i, 'body_html'):  # is comment
                body = i.body_html

                # html output
                output = html_output_string(permalink, author, body)
                if delete_files is False:
                    file_name = html_writer(name, output)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_html(output)
                    enclient.add_tag(*evernote_tags)  # the * is very important. It unpacks the tags tuple properly
                    note = enclient.create_note()

            elif hasattr(i, 'is_self') and i.is_self is True:  # is self post
                text = i.selftext_html

                # html output
                output = html_output_string(permalink, author, text)
                if delete_files is False:
                    file_name = html_writer(name, output)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_html(output)
                    note = enclient.create_note()

            elif hasattr(i, 'url') and re.sub("([^A-z0-9])\w+", "", i.url.split('.')[-1]) in ['jpg', 'png', 'gif', 'gifv', 'pdf']:  # is direct image.
                """
                Need to check file types and test pdf. How does this handle gfycat and webm? Can EN display that inline?
                The regex in the if is to strip out non-valid filetype chars.
                """
                url = i.url
                base_filename = "{}_image.{}".format(name, re.sub("([^A-z0-9])\w+", "", url.split('.')[
                    -1]))  # filename for image. regex same as above.
                filename = "Downloads/" + base_filename

                # image downloader section
                image_downloaded = image_saver(url, filename)
                if image_downloaded:
                    # write image as <img> or link to local pdf downloaded in html file
                    if filename.split('.')[-1] == 'pdf':
                        img = '<a href="{}">Click here for link to downloaded pdf</a>'.format(base_filename)
                    else:
                        img = '{0}<br><br><a href="{1}"><img src="{1}"></a>'.format(i.title,
                                                                                    base_filename)  # html for embedding in html file
                else:
                    img = "Image failed to download - It may be temporarily or permanently unavailable"

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_text(html_output_string(permalink, author, ""))  # should add body="" in the function
                    if image_downloaded:
                        enclient.add_resource(filename)
                    note = enclient.create_note()

                if delete_files is False:
                    file_name = html_writer(name, html_output_string(permalink, author, img))
                else:
                    os.remove(filename)
            elif hasattr(i, 'url') and 'imgur' in i.url:  # is imgur album. Add option to download images to folder.
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

                path = 'Downloads/{}'.format(gallery_id)
                if not os.path.exists(path):
                    os.makedirs(path)
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
                    filename = path + "/" + base_filename
                    if not os.path.exists(filename):  # only download if file doesn't already exist
                        image_saver(image_link, filename)
                    body += img

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    if len(gallery) == 1 and filename is not None:
                        enclient.add_html(html_output_string(permalink, author, ""))
                        enclient.add_resource(filename)
                    else:
                        enclient.add_text(html_output_string(permalink, author,
                                                             'This album is too large to embed; please see '
                                                             '<a href="{}">here</a> for the original link.'.format(url)))
                    note = enclient.create_note()

                if delete_files is False:
                    file_name = html_writer(name, html_output_string(permalink, author, body))
                else:
                    shutil.rmtree(path)

            elif hasattr(i, 'title') and i.is_self is False:  # is article
                # This section needs work. It is semi-complete. Ultimately, adding in the full article is the goal.
                url = i.url

                # readability api section
                parse = ParserClient(credentials['readability']['parser_key'])
                parse_response = parse.get_article(url)
                article = parse_response.json()
                if 'content' not in article:  # if unable to parse document, manually set an error message
                    article['content'] = 'Unable to parse page - See <a href="{}">here</a> for the original link'.format(url)
                article = article['content']
                article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article

                # html output section.
                output = html_output_string(permalink, author, article)
                if delete_files is False:
                    file_name = html_writer(name, output)

                # Evernote section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    output = html_output_string(permalink, author, article)
                    enclient.add_html(output)

                    # Add html file to note
                    # enclient.add_resource("Downloads/{}.html".format(name))
                    note = enclient.create_note()

            # end of checking for saved items #

            if not debug_mode:  # write index items normally, otherwise diasble for easier testing
                ind.write(name + "\n")
                ind.flush()  # this fixes python not writing the file if it terminates before .close() can be called
                if delete_files is False:
                    html_index_file.add_link(title, file_name, permalink)
            if use_evernote is True and note is not None:
                print("Saved {:9} - GUID: {}".format(name, note.guid))
            elif use_evernote is True:
                print("Saved {:9} - Note failed to upload".format(name))
            else:  # is debug mode
                print("Saved " + name)

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
