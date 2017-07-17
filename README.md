# SavedRetriever #

SR is a self-hosted python script that will fetch the users saved comments and posts from reddit and download them locally. SR will save files to a local folder called 'SRDownloads' which contains all the saved items of the users account. SR will save comments, self posts, direct linked images, imgur albums and text based articles. Readability is used to parse webpages for content, which may result in some pages not saving correctly, however, most text based pages (eg news articles) can be saved without issue.

Requires Python 3.

Screenshots:
![Home](http://i.imgur.com/N8AtGFO.png)
![Image post](http://i.imgur.com/KTjiGkH.png)

----------

To run
======

 1. Download folder and extract the zip, or clone, then navigate to the directory and run:

	 `pip install -r requirements.txt`

 2. Then navigate up one level to the download location and run the name of the folder, eg:

	 `python flask_app.py`

 This will start the app on port 5000
 3. Visit localhost:5000 then visit the settings page and follow the authentication wizard to authenticate with reddit and get your access token.

Using a virtualenv is recommended. This can be achieved by:
 virtualenv -p python3 env
 source env/bin/activate or source env/bin/activate.fish if using the fish shell
 "pip install -r requirements.txt" to install the required python packages

## Commandline switches ##
The following commandline switches are available:

- -e, -evernote: when present, SR will attempt to upload saved items to evernote.
- -debug: when present, items will not be added to the index or the html index file, to allow for easier testing. Debug level log will also be collected
- -i: When present, SR will print the log to the console as well as the log file at info level.

## 3rd Party libraries ##
SR uses the following 3rd party libraries:

 - [PRAW](https://github.com/praw-dev/praw/tree/v3.0.0)
 - [Bleach](https://github.com/jsocol/bleach)
 - [Readability API](https://github.com/arc90/python-readability-api)
 - [Imgur API](https://github.com/Imgur/imgurpython)
 - [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/bs4/doc/)
 - [Lxml](http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml) Required for windows. For fedora need to install "redhat-rpm-config", ubuntu may need 'python3-dev'
