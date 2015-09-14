import logging
import os


class index:
    """
    This class generates an index file of the saved links so that they can be easily viewed in a browser.
    If the index file does not exist, it will create it. Each item that is added is appended as part of an unordered list, with the title (which is a link to the downloaded item) and a link to the permalink of the saved item.
    """
    def __init__(self, username, path):
        """
        Opens the index file, or creates it and adds initial html.
        :param username:
        :type username: string
        :return:
        :rtype:
        """
        logger = logging.getLogger(__name__)
        path += '/_index.html'
        if not os.path.isfile(path):
            logger.debug('Creating new index file')
            self.file = open(path, 'a')  # create index for writing.
            self.file.write(
                "<head><style>\n"
                "body{{margin: 0;}} html {{font-family:'Roboto', 'Georgia', sans-serif; font-weight:400;}} "
                "h3 {{font-family:'Roboto', 'Tahoma', sans-serif; font-weight:700;}} "
                ".navbar {{background-color: #3F51B5; padding-top: 5px; padding-bottom: 5px; padding-left: 5px; margin-bottom: 10px; color: white;}}"
                ".navbar a:link {{color: #ffffff;}}.navbar a:visited {{color: #ffffff;}}.navbar a:hover {{color: #B6B6B6;}}\n"
                "</style>\n"
                "<title>saved by {0}</title>\n"
                "<link href='https://fonts.googleapis.com/css?family=Roboto:400,700' rel='stylesheet' type='text/css'>"
                "</head>"
                "<div class='navbar'><h3>Index of files saved by <a href=\"http://www.reddit.com/user/{0}\">/u/{0}</a></h3></div>\n"
                "<ul>\n".format(username)
            )  # This is not completely valid html, as the <ul> tag will not be closed; most web browsers should
            #    ignore this and render the page properly.
        else:
            logger.debug('Opening existing index file')
            self.file = open(path, 'a')  # otherwise open for appending without initial html

    def add_link(self, title, local_url, remote_url):
        """
        Writes a new link to the index.
        :param title:
        :type title: string
        :param local_url:
        :type local_url: string
        :param remote_url:
        :type remote_url: string
        :return:
        :rtype:
        """
        self.file.write(
            '    <li><a href="{}">{}</a> | <a href="{}">Original</a></li>\n'.format(local_url, title, remote_url)
        )  # write the link and title to a list. New line is for formatting of file itself.
        self.file.flush()

    def save_and_close(self):
        """
        This must be called once the script is done adding things to the index file, or the file will not be properly closed
        :return:
        :rtype:
        """
        self.file.close()
