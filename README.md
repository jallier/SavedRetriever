#SavedRetriever #

SR is a python script that will fetch the users saved comments and posts from reddit and downloaded them locally, as well as uploading to evernote. Authenticates using Oauth, but this needs some work. 

----------

To run
======

In order to run the program, you will need to get your own access tokens from the services listed below.
This means that you will need an account for each of the required services, and will need to register new apps for each of them.
Once the folder is downloaded:

 1. First ensure you have created a new personal script at [https://www.reddit.com/prefs/apps/](https://www.reddit.com/prefs/apps/) 
 2. Then run
>python main.py

 3. This will interactively authenticate with reddit and generate the config file. From there, edit the config so that the relevant access tokens are filled in. See the list of services below for where to get them.
 4. The script can then be run normally and will use the provided tokens.

##ToDo##

 - Save console output to file
 - Dropbox integration?
 - add console output only when debug flag present.

##Services required##
As of version 0.9, SR requires the use of the these 3rd party services. This means that a valid account and developer oauth tokens are needed for each of the following services (ie. you must register an app of your own and use the tokens they give you):

 - Reddit - [reddit.com](www.reddit.com)
 - Readability - [readability.com](www.readability.com)
 - Imgur - [imgur.com](www.imgur.com)
 - Evernote - [evernote.com](www.dev.evernote.com)
>Note: Evernote is recommended, but not required. In future versions some of these may become optional.

##Commandline switches##
The following commandline switches are available:

- -e, -evernote: when present, SR will attempt to upload saved items to evernote.
- -debug: when present, items will not be added to the index, to allow for easier testing,

##3rd Party libraries##
SR uses the following 3rd party libraries:

 - [PRAW](https://github.com/praw-dev/praw/tree/v3.0.0)
 - [Bleach](https://github.com/jsocol/bleach)
 - [Evernote API (for python 3)](https://github.com/evernote/evernote-sdk-python3)
 - [Readability API](https://github.com/arc90/python-readability-api)
 - [Imgur API](https://github.com/Imgur/imgurpython)