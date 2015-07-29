__author__ = 'fuzzycut'

import json
# import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient
import hashlib
import binascii
import evernote
import re
import bleach


class Client:
    def __init__(self, token, notebook_name='default'):
        try:
            self.client = EvernoteClient(token=token, sandbox=True)
        except:
            raise SystemExit  # no point continuing if this doesn't work.
        self.note_store = self.client.get_note_store()
        self.tag_list = self.note_store.listTags()
        self.notebooks = self.note_store.listNotebooks()
        self.notebook_name = notebook_name  # for use in other functions.
        self.notebook_guid = None
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

        # xml for note content
        self.start_xml_tag = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM ' \
                             '"http://xml.evernote.com/pub/enml2.dtd"><en-note>'
        self.content = ""
        self.end_xml_tag = '</en-note>'
        self.note = None

    def new_note(self, title):  # Should this be a separate class?
        self.note = Types.Note()
        self.note.title = title[:252] + "..."  # truncates title length to fit evernote
        self.note.content = self.start_xml_tag
        if self.notebook_name != 'default':
            self.note.notebookGuid = self.notebook_guid
        return

    def add_text(self, text):
        """
        Adds text content to the note. Adds a new line at the end of the text.
        :param text:
        :return:
        """
        self.note.content += text + "<br/>"  # need try block to test if note already exists.
        return

    def add_resource(self, filename):
        """
        Adds a resource (image or pdf at this stage) to the note. Adds a new line at the end of the attachment
        :param filename:
        :return:
        """
        accepted_mimes = {
            'gif': 'image/gif', 'jpg': 'image/jpeg', 'png': 'image/png', 'pdf': 'application/pdf', 'html': 'text/html'}
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
        resource.fileName = filename
        # resource.attachment = True

        if not self.note.resources:
            self.note.resources = [resource]
        else:
            self.note.resources += [resource]

        hash_hex = binascii.hexlify(hashed_resource)
        hash_str = hash_hex.decode("UTF-8")

        self.note.content += '<en-media type="{}" hash="{}"/><br/>'.format(mime_type, hash_str)
        return

    def create_note(self):
        """
        Adds the completed note to the default evernote notebook.
        :return:
        """
        self.note.content += self.end_xml_tag
        try:
            created_note = self.note_store.createNote(self.note)  # this may result in errors if malformed xml
        except:
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
        :param output_text:
        :return:
        """
        if sanitize is True:
            self.add_text(self.html_to_enml(self.santize_html(input_html)))
        else:
            self.add_text(input_html)
        return

    def html_to_enml(self, html_content):
        """
        Helper function for add_html method. Shouldn't need to be called by itself.
        """
        output_text = html_content

        output_text = re.sub("<br>", "<br/>", output_text)  # fixes br tag for evernote

        output_text = re.sub("[^\x00-\x9C4]", "-", output_text)  # need to investigate: need to exclude dashes. Is this still necessary?

        output_text = re.sub('(<a href="[^http].*?</a>)', '-removed-', output_text)  # Removes invalid <a> tags

        pattern = 'href=".*?"'  # wow this is ugly. Fixes subreddit linking
        matches = re.finditer(pattern, output_text)
        for i in matches:
            full_match = i.group()
            match = full_match.split('"')
            if match[1][0:3] == '/r/':
                output_text = re.sub(full_match, 'href="http://www.reddit.com/r/{}"'.format(match[1][3:]), output_text)

        # pattern = '<img.*?>'  # pattern for properly closing img tags
        # matches = re.findall(pattern, output_text)
        # for match in matches:  # loops through all img tag mathches and adds closing tag
        #     output_text = re.sub(match, match + "</img>", output_text)
        #
        # pattern = '<a.*?>'  # pattern for properly closing img tags
        # matches = re.findall(pattern, output_text)
        # for match in matches:  # loops through all img tag mathches and adds closing tag
        #     output_text = re.sub(match, match + "</a>", output_text)

        return output_text

    def santize_html(self, input_html):
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
            'td'
        ]
        allowed_attrs = {
            '*': ['href', 'src']
        }
        return bleach.clean(input_html, tags=allowed_tags, attributes=allowed_attrs, strip=True)

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
