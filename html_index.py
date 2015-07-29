import os

__author__ = 'Justin'


class index:
    def __init__(self, username):
        if not os.path.isfile('Downloads/_index.html'):
            self.file = open('Downloads/_index.html', 'a')  # create index for writing.
            self.file.write(
                "<head><style>\n"
                "img {{max-width:100%;}}body {{font-family: Calibri;}}\n"
                "</style></head>\n"
                "<h3>Index of files saved by <a href=\"http://www.reddit.com/user/{0}\">/u/{0}</a></h3>\n"
                "<ul>\n".format(username)
            )  # This is not completely valid html, as the <ul> tag will not be closed; most web browsers should
            # ignore this and render the page properly.
        else:
            self.file = open('Downloads/_index.html', 'a')  # otherwise open for appending without initial html

    def add_link(self, title, local_url, remote_url):
        """
        Add a new link to the index file.
        """
        self.file.write(
            '    <li><a href="{}">{}</a> | <a href="{}">Original</a></li>\n'.format(local_url, title, remote_url)
        )  # write the link and title to a list. New line is for formatting of file itself.

    def save_and_close(self):
        """
        This must be called once the script is done adding things to the index file, or the file will not be properly closed
        :return:
        :rtype:
        """
        self.file.close()
