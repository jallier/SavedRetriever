import datetime
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient
import evernote.edam.error
import hashlib
import binascii
import re
import bleach
from bs4 import BeautifulSoup
from Resources.CommonUtils import Utils


def html_to_enml(html_content):
    """
    Helper function for add_html method. Shouldn't need to be called by itself.
    :param html_content: html content to add
    :type html_content: string
    :rtype: string
    """
    allowed_tags = [
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
    allowed_attrs = {
        '*': ['href', 'src']
    }
    output_text = bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attrs,
                               strip=True)  # removes disallowed elements from document for evernote

    output_text = re.sub("<br>|</br>", "<br/>", output_text)  # fixes br tag for evernote

    # output_text = re.sub("[^\x00-\x9C4]", "-",
    #                      output_text)  # need to investigate: need to exclude dashes. Is this still necessary?

    output_text = re.sub('(<a href="[^htp].*?</a>)', '-removed-', output_text)  # Removes invalid <a> tags

    pattern = 'href=".*?"'  # wow this is ugly. Fixes subreddit linking
    matches = re.finditer(pattern, output_text)
    for i in matches:
        full_match = i.group()
        match = full_match.split('"')
        if match[1][0:3] == '/r/':
            output_text = re.sub(full_match, 'href="http://www.reddit.com/r/{}"'.format(match[1][3:]), output_text)

    soup = BeautifulSoup(output_text, "html.parser")
    output_text = str(soup)

    return output_text


class Client:
    def __init__(self, token, notebook_name='default'):
        """
        Initializes the evernote client for uploading notes.
        :param token: the developer token needed for access to the account
        :type token: string
        :param notebook_name: name of notebook to add the new notes to.
        :type notebook_name: string
        """
        client = None
        try:  # Should make sandbox a debug option
            client = EvernoteClient(token=token, sandbox=True)
        except evernote.edam.error.ttypes.EDAMUserException:
            print("Please provide correct evernote credentials")
            if input("Abort (y/n): ") == 'y':  # Might be best to just silently try again or continue rather than ask.
                raise SystemExit
        self.user_store = client.get_user_store()
        self.note_store = client.get_note_store()
        self.tag_list = self.note_store.listTags()
        self.notebooks = self.note_store.listNotebooks()
        self.notebook_name = notebook_name  # for use in other functions.
        self.notebook_guid = None
        self.error_count = 0
        self.warning_count = 0

        self.quota_remaining()

        if notebook_name != 'default':  # ie we want to specify the notebook to save the notes to
            notebook_dic = {}
            for notebook in self.notebooks:  # create dict of notebook names: notebook objects
                notebook_dic[notebook.name] = notebook

            if notebook_name in notebook_dic:  # if notebook exists, set persistant guid as existing guid
                self.notebook_guid = notebook_dic[notebook_name].guid
            else:  # if it doesn't exist, create it.
                new_notebook = Types.Notebook()
                new_notebook.name = notebook_name
                new_notebook.defaultNotebook = False
                self.notebook_guid = self.note_store.createNotebook(new_notebook).guid

        self.note = None

    def new_note(self, input_title):  # Should this be a separate class?
        self.note = Types.Note()
        title = input_title
        if title.endswith(' '):  # Spaces at the end seem to prevent the note uploading, so this works around that.
            title = title[:-1]
        self.note.title = (title[:252] + "...") if len(title) > 252 else title  # truncates title length to fit evernote. Thanks SO.
        self.note.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM ' \
                            '"http://xml.evernote.com/pub/enml2.dtd"><en-note>'
        if self.notebook_name != 'default':
            self.note.notebookGuid = self.notebook_guid
        return

    def add_text(self, text):
        """
        Adds text content to the note. Adds a new line at the end of the text.
        :param text: text to add to the note
        :type text: string
        :return:
        """
        self.note.content += text + "<br/>"  # need try block to test if note already exists.
        return

    def add_resource(self, filename):
        """
        Adds a resource (image or pdf at this stage) to the note. Adds a new line at the end of the attachment
        :param filename: name of the file to add to the note
        :type filename: string
        :return:
        """
        accepted_mimes = {
            'gif': 'image/gif', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'pdf': 'application/pdf', 'html': 'text/html'}
        # ^these are mime types that can be displayed inline in the client. Also the only type that will be directly
        # downloaded by the downloader. Will need more testing. Others can be added later.
        extention = filename.split('.')[-1]
        mime_type = accepted_mimes[extention]
        with open(filename, 'rb') as f:
            attachment = f.read()
        # hashing the attachment
        md5 = hashlib.md5()
        md5.update(attachment)
        hashed_resource = md5.digest()
        # adding the attachment as data Type
        data = Types.Data()
        data.size = len(attachment)
        data.bodyHash = hashed_resource
        data.body = attachment
        # adding the data to the note.
        resource = Types.Resource()
        resource.mime = mime_type
        resource.data = data
        resource.attributes = Types.ResourceAttributes()
        resource.attributes.fileName = filename
        # resource.attachment = True

        if not self.note.resources:
            self.note.resources = [resource]
        else:
            self.note.resources += [resource]

        hash_hex = binascii.hexlify(hashed_resource)
        hash_str = hash_hex.decode("UTF-8")

        self.note.content += '<en-media type="{}" hash="{}"/><br/>'.format(mime_type, hash_str)
        return

    def quota_remaining(self, upload_failed=False):
        user = self.user_store.getUser()
        state = self.note_store.getSyncState()

        total_monthly_quota = user.accounting.uploadLimit
        used_so_far = state.uploaded
        quota_remaining = total_monthly_quota - used_so_far

        FIVE_MEGABYTES = 5242880
        if upload_failed and self.error_count == 0:
            reset_date = datetime.datetime.fromtimestamp(user.accounting.uploadLimitEnd / 1000.0)
            today = datetime.datetime.today()
            print("Upload failed - Upload quota exceeded. Data allowance resets in {} days".format(
                (reset_date - today).days))
            self.error_count += 1
        elif quota_remaining < FIVE_MEGABYTES and self.warning_count == 0:
            print("\nWarning! You have less than 5 MB of evernote upload data remaining. Data remaining: {}\n".format(
                Utils.human_readable_filesize(quota_remaining)))
            self.warning_count += 1

    def create_note(self):
        """
        Adds the completed note to the default evernote notebook.
        :return: Returns a note object of the created note
        :rtype: Types.Note
        """
        self.note.content += '</en-note>'  # enml closing tag
        created_note = None
        try:
            created_note = self.note_store.createNote(self.note)  # this may result in errors if malformed xml
        except evernote.edam.error.ttypes.EDAMUserException as error:
            if error.errorCode == 7:
                self.quota_remaining(upload_failed=True)
                # add option to continue downloading locally, or just wait until the next month.
            else:
                print(self.note)
                raise
        self.note = None  # resets note. This is because im unsure how python handles objects in a for loop
        return created_note

    def print_note(self):
        print(self.note)

    def add_html(self, input_html, sanitize=True):
        """
        Converts html to ENML suitable for storage as note, while retaining some html formatting,
        then adds it to the current note.
        This method is NOT comprehensive. It will only strip classes from tags, close <br> tags and <img> tags
        More conversions will be added as needed.
        :param input_html: string of the html to add to the note.
        :type input_html: string
        :return:
        """
        if sanitize is True:
            self.add_text(html_to_enml(input_html))
        else:
            self.add_text(input_html)
        return

    def add_tag(self, *input_tags):
        """
        This method adds tags to the current note. As such it must be called AFTER a new note is created.
        Takes either a single string, or a list or tuple of strings. If a list or tuple is used, it must be called using
        a * in front of the list/tuple. eg Wrapper.add_html(*(1,2,3)).
        If this is not done the method cannot loop through the tags properly.
        :param input_tags:
        :type input_tags:
        :return:
        :rtype:
        """
        self.tag_list = self.note_store.listTags()  # gets new list of tags that may have been created since Wrapper object creation
        tag_list = {}
        for tag in self.tag_list:  # create dict of tag names: tag objects
            tag_list[tag.name] = tag

        for tag in input_tags:
            if tag not in tag_list:  # if tag name does not exist; create it
                new_tag = Types.Tag()
                new_tag.name = tag
                # create tag and add it to current note
                guid = self.note_store.createTag(
                    new_tag).guid  # Might want to add try block here. EN can't handle tags with different cased letters
                if not self.note.tagGuids:  # if note has no other tags
                    self.note.tagGuids = [guid]
                else:  # if note already has some tags
                    self.note.tagGuids += [guid]
            else:  # tag already exists
                if not self.note.tagGuids:  # if note has no other tags
                    self.note.tagGuids = [tag_list[tag].guid]
                else:  # if note already has other tags
                    self.note.tagGuids += [tag_list[tag].guid]
        return
