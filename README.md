#SavedRetriever #

SR is a python script that will fetch the users saved comments and posts from reddit and download them locally, as well as uploading to evernote. SR will save files to a local folder called 'SRDownloads' which contains all the saved items of the users account. SR will save comments, self posts, direct linked images, imgur albums and text based articles. Readability is used to parse webpages for content, which may result in some pages not saving correctly, however, most text based pages (eg news articles) can be saved without issue.

Requires Python 3. 

----------

To run
======

In order to run the program, you will need to get your own access tokens from the services listed below.
This means that you will need an account for each of the required services, and will need to register new apps for each of them.
Once the folder is downloaded:

 1. First ensure that you have created a new personal script at [reddit](https://www.reddit.com/prefs/apps/), [imgur](https://imgur.com/signin?redirect=http://api.imgur.com/oauth2/addclient) and [readability](https://www.readability.com/login/?next=/settings/account)
 2. Download folder and extract the zip, or clone, then navigate to the directory and run:

	 `pip install -r requirements.txt`

 3. Then navigate up one level to the download location and run the name of the folder, eg:
	 
	 `python SavedRetriever-master`

 4. This will interactively authenticate with reddit and generate the config file. From there, edit the config so that the relevant access tokens are filled in. See the list of services below for where to get them.
 5. The script can then be run normally and will use the provided tokens. eg

	 `python SavedRetriever -e -p /home/Downloads/Reddit/`

Using a virtualenv is recommended. This can be achieved by:
 virtualenv -p python3 env
 source env/bin/activate or source env/bin/activate.fish if using the fish shell
 "pip install -r requirements.txt" to install the required python packages

	
##Services required##
As of version 0.9, SR requires the use of the these 3rd party services. This means that a valid account and developer oauth tokens are needed for each of the following services (ie. you must register an app of your own and use the tokens they give you):

 - Reddit - [reddit.com](www.reddit.com) - You must register a new script-type app [here.](https://www.reddit.com/prefs/apps/) Set the name as anything you like, and the redirect uri as http://127.0.0.1:65010/authorize_callback
 - Readability - [readability.com](www.readability.com) - Log in/register, then see [here](https://www.readability.com/developers/api) to get access tokens
 - Imgur - [imgur.com](www.imgur.com) - Log in/register, then see [here](https://api.imgur.com/oauth2/addclient?) to get access tokens. Register an app without a callback url
 - Evernote - [evernote.com](www.dev.evernote.com) - Log in/register, then see [here](https://www.evernote.com/api/DeveloperToken.action) to get personal developer token

>Note: Evernote is recommended, but not required.

Readability is required to parse articles into more readable text, and imgur is required to download albums (the majority of albums posted to reddit are from imgur)

##Commandline switches##
The following commandline switches are available:

- -e, -evernote: when present, SR will attempt to upload saved items to evernote.
- -debug: when present, items will not be added to the index or the html index file, to allow for easier testing. Debug level log will also be collected
- -p, -path: Specifies where you would like the save the files. If not specified, will download to current directory. eg -p /home/hallj/Documents/
- -t: When present, SR will delete any files it downloads once it has uploaded them to evernote. (Partially implemented) Only available when using evernote
- -i: When present, SR will print the log to the console as well as the log file at info level.

##3rd Party libraries##
SR uses the following 3rd party libraries:

 - [PRAW](https://github.com/praw-dev/praw/tree/v3.0.0)
 - [Bleach](https://github.com/jsocol/bleach)
 - [Evernote API (for python 3)](https://github.com/evernote/evernote-sdk-python3)
 - [Readability API](https://github.com/arc90/python-readability-api)
 - [Imgur API](https://github.com/Imgur/imgurpython)
 - [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/bs4/doc/)
 - [Lxml](http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml) Required for windows. For fedora need to install "redhat-rpm-config"
