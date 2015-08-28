from setuptools import setup

setup(
    name='SavedRetriever',
    version='1.0.2',
    author='hallj',
    author_email='fuzzy_cut@hotmail.com',
    packages=['savedretriever.Resources', 'savedretriever'],
    url='https://github.com/hallj/SavedRetriever/',
    license='LICENSE',
    description='Saves saved items from Reddit',
    long_description=open('README').read(),
    install_requires=[
        "praw >= 3.0.0",
        "bleach >= 1.4.1",
        "readability-api >= 1.0.0",
        "imgurpython >= 1.1.6",
        "beautifulsoup4 >= 4.4.0",
        "evernote <= 1.25.2"
    ],
    dependency_links=[
        'https://github.com/evernote/evernote-sdk-python3/tarball/master#egg=evernote-1.25.2'
    ]
)
