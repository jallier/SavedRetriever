import praw
import json
import urllib.request
import os
from readability import ParserClient
from imgurpython import ImgurClient
import evernoteWrapper
import argparse
import evernote.edam.error
import firstrun
import codecs
import re
import html_index

__author__ = 'fuzzycut'
"""
Retreives saved content from reddit.

TODO:
    - Optimise code
    - Check EN if note exists?
    - Dropbox support
    - Investigate using Goose to parse articles.
"""


def html_writer(file, output):
    """
    Writes an html file.

    Takes: the name of the file to write and the content (string) to write.
    Returns: the relative path of the downloaded file. (Relative to location of script)
    """
    # f = open("Downloads/{}.html".format(file_name), 'w')  # Change this once you get evernote functionality going.
    file_name = "Downloads/{}.html".format(file)
    name = file + ".html"
    f = codecs.open(file_name, 'w', 'utf-8')
    html_image_size = "<head>\n<style>\nimg {max-width:100%;}\n</style>\n</head>\n"
    f.write(html_image_size + output)
    f.close()
    return name


def html_output_string(permalink, author, body):
    """
    defines a global string to use to neaten up the output sections
    Returns a string of the html output for the items.
    """
    return '<a href="{}">{}</a><br/>by <a href="http://www.reddit.com/u/{}">/u/{}</a><br/><br/>{}'.format(permalink,
                                                                                                          permalink,
                                                                                                          author,
                                                                                                          author,
                                                                                                          body)


def image_saver(url, filename):
    try:
        with urllib.request.urlopen(url) as response, open(filename, "wb") as out_file:
            data = response.read()
            out_file.write(data)
    except urllib.error.HTTPError:
        return False
    return True


def get_reddit_user(credentials):
    client_ID = credentials['reddit']['client_id']
    client_secret = credentials['reddit']['client_secret']
    redirect_URI = credentials['reddit']['redirect_uri']
    refresh_token = credentials['reddit']['refresh_token']
    user_agent = "SavedRetriever 0.9 by /u/fuzzycut"

    r = praw.Reddit(user_agent=user_agent,
                    oauth_client_id=client_ID,
                    oauth_client_secret=client_secret,
                    oauth_redirect_uri=redirect_URI)

    access_information = r.refresh_access_information(refresh_token)
    r.set_access_credentials(**access_information)
    return r.get_me()


def read_command_args():
    """
    Reads commandline switches and returns an object containing the values of the switches
    :return:
    :rtype:
    """
    parser = argparse.ArgumentParser(description="Determine which services to use")
    parser.add_argument('-debug', action='store_true', default=False)
    parser.add_argument('-e', '-evernote', action='store_true', default=False)
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

    me = get_reddit_user(credentials)

    if not os.path.exists("Downloads"):
        os.makedirs("Downloads")

    if os.path.isfile('index.txt'):  # checking for  index file, which contains index of downloaded files.
        with open('index.txt', 'r') as ind:
            index = ind.read()
        index = index.split()
    else:
        index = []

    if use_evernote is True:
        try:
            enclient = evernoteWrapper.Client(
                credentials['evernote']['dev_token'],
                'Saved from Reddit')  # This will need to change once EN is switched to production
        except evernote.edam.error.ttypes.EDAMUserException:
            print("Please provide correct evernote credentials")
            if input("Abort (y/n): ") == 'y':  # Might be best to just silently continue rather than ask.
                raise SystemExit

    html_index_file = html_index.index(me.name)
    ind = open('index.txt', 'a')  # open index file for appending
    for i in me.get_saved(limit=None):  # change this limit later
        name = i.name
        evernote_tags = ('Reddit', 'SavedRetriever', '/r/' + i.subreddit.display_name)  # add config for this later
        if name not in index:
            print(name)
            print(dir(i))  # get rid of this after testing.
            if hasattr(i, 'body_html'):  # is comment
                permalink = i.permalink
                body = i.body_html
                author = i.author
                title = "{} comments from {}".format(author, i.link_title)

                # html output
                output = html_output_string(permalink, author, body)
                file_name = html_writer(name, output)
                html_index_file.add_link(i.link_title, file_name, permalink)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_html(output)
                    enclient.add_tag(*evernote_tags)  # the * is very important. It unpacks the tags tuple properly
                    note = enclient.create_note()
                    print(note.guid)

            elif hasattr(i, 'is_self') and i.is_self is True:  # is self post
                text = i.selftext_html
                permalink = i.permalink
                author = i.author
                title = i.title

                # html output
                output = html_output_string(permalink, author, text)
                file_name = html_writer(name, output)
                html_index_file.add_link(title, file_name, permalink)

                # en api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_html(output)
                    note = enclient.create_note()
                    print(note.guid)

            elif hasattr(i, 'url') and re.sub("([^A-z0-9])\w+", "", i.url.split('.')[-1]) in ['jpg', 'png', 'gif', 'gifv', 'pdf']:  # is direct image.
                """
                Need to check file types and test pdf. How does this handle gfycat and webm? Can EN display that inline?
                The horrendous regex in the if is to strip out non-valid filetype chars. Shudder
                """
                url = i.url
                author = i.author
                permalink = i.permalink
                title = i.title
                base_filename = "{}_image.{}".format(name, re.sub("([^A-z0-9])\w+", "", url.split('.')[
                    -1]))  # filename for image. Ugly regex same as above.
                filename = "Downloads/" + base_filename

                # image downloader section
                image_downloaded = image_saver(url, filename)
                if image_downloaded:
                    # write image as <img> or link to local pdf downloaded in html file
                    if filename.split('.')[-1] == 'pdf':
                        img = '<a href="{}">Click here for link to downloaded pdf</a>'.format(base_filename)
                    else:
                        img = "{}<br><br><img src='{}'>".format(i.title, base_filename)  # html for embedding in html file
                else:
                    img = "Image failed to download - It may be temporarily or permanently unavailable"

                file_name = html_writer(name, html_output_string(permalink, author, img))
                html_index_file.add_link(title, file_name, permalink)

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_text(html_output_string(permalink, author, ""))  # should add body="" in the function
                    if image_downloaded:
                        enclient.add_resource(filename)
                    note = enclient.create_note()
                    print(note.guid)
            elif hasattr(i, 'url') and 'imgur' in i.url:  # is imgur album. Add option to download images to folder.
                url = i.url
                author = i.author
                permalink = i.permalink
                title = i.title
                body = "<h2>{}</h2>".format(title)

                # imgur api section
                client = ImgurClient(credentials['imgur']['client_id'], credentials['imgur']['client_secret'])
                gallery_id = url.replace('?', '/')
                gallery_id = gallery_id.split('/')[-1]  # gets the id of the gallery.
                print(url)
                pattern = "([A-z0-9])\w+"  # this regex is to try deal with unusual gallery names
                match = re.search(pattern, gallery_id)  # it parses out non alphabet (ie non-valid id) characters
                gallery_id = match.group(0)
                try:
                    gallery = client.get_album_images(gallery_id)
                except:  # this deals with a strange issue where a single image is listed as an album
                    # need to investigate: this masks other typos in the gallery names (such as &gallery that is appended sometimes)
                    # print(url, gallery_id)
                    try:
                        gallery = [client.get_image(gallery_id)]
                    except:
                        gallery = []
                # ^ wow this block is ugly. Should probably look into error handling a bit better.
                path = 'Downloads/{}'.format(gallery_id)
                if not os.path.exists(path):
                    os.makedirs(path)
                for image in gallery:  # add if gallery > 10, then just add a link (would be too large for the note)
                    image_name = image.title
                    if image_name == "None":
                        image_name = ""
                    image_description = image.description
                    if image_description == "None":
                        image_description = ""
                    image_filetype = image.type.split('/')[1]
                    image_id = image.id
                    image_link = image.link
                    # sets up downloaded filename and html for embedding image
                    base_filename = "{}_image.{}".format(image_id, image_filetype)
                    img = "<p><h3>{}</h3><img src=\"{}/{}\"><br/>{}</p>".format(image_name, gallery_id, base_filename,
                                                                                image_description)
                    filename = path + "/" + base_filename
                    if not os.path.exists(filename):  # only download if file doesn't already exist
                        image_saver(image_link, filename)
                    body += img
                file_name = html_writer(name, html_output_string(permalink, author, body))
                html_index_file.add_link(title, file_name, permalink)

                # Evernote api section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    enclient.add_text(html_output_string(permalink, author,
                                                         'This album is too large to embed; please see '
                                                         '<a href="{}">here</a> for the original link.'.format(url)))
                    note = enclient.create_note()
                    print(note.guid)

            elif hasattr(i, 'title') and i.is_self is False:  # is article
                # This section needs work. It is semi-complete. Ultimately, adding in the full article is the goal.
                url = i.url
                author = i.author
                permalink = i.permalink
                title = i.title

                # readability api section
                parse = ParserClient(credentials['readability']['parser_key'])
                parse_response = parse.get_article(url)
                article = parse_response.json()
                if 'content' not in article:  # if unable to parse document, manually set an error message
                    article['content'] = "Unable to parse page"
                article = article['content']
                article = "<a href='{}'>{}</a><br/>{}<br/>".format(url, title, article)  # source of article

                # html output section.
                output = html_output_string(permalink, author, article)
                file_name = html_writer(name, output)
                html_index_file.add_link(title, file_name, permalink)

                # Evernote section
                if use_evernote is True:
                    enclient.new_note(title)
                    enclient.add_tag(*evernote_tags)
                    output = html_output_string(permalink, author,
                                                '<br/><a href="{}">{}</a><br/>Source cannot be stored in evernote '
                                                '(blame their stupid API.) See source above, or attached html file'.format(
                                                    url, title))
                    enclient.add_html(output)

                    # Add html file to note
                    enclient.add_resource("Downloads/{}.html".format(name))
                    note = enclient.create_note()
                    print(note.guid)
            else:
                pass
            print("\n")
            if debug_mode is False:  # if not in debug, then write index items normally, otherwise diasble for easier
                ind.write(name + "\n")  # testing

    # end of for loop
    ind.close()
    html_index_file.save_and_close()

    raise SystemExit  # This is to fix some random ssl socket error.


main()
