#!/usr/bin/env python
import sys
import praw


def authenticate_reddit():
    print(
        "Please ensure that you have the relevant tokens for the services required and fill these in after "
        "authenticating with reddit. See the readme for where to get them")
    print("Before you can complete this authentication you must register the app at https://www.reddit.com/prefs/apps/")
    client_id = input("Client ID: ")
    client_secret = input("Client Secret: ")
    redirect_uri = input("Redirect URI (set to http://127.0.0.1:65010/authorize_callback): ")
    scope = 'identity history read'

    r = praw.Reddit('easy-oauth.py client',
                    oauth_client_id=client_id,
                    oauth_client_secret=client_secret,
                    oauth_redirect_uri=redirect_uri
                    )

    print("Visit the following link, and click allow:\n" + r.get_authorize_url('SavedRetriever by /u/fuzzycut', scope,
                                                                               True))
    access_code = input('Copy code from url in browser, then enter code: ')
    access_information = r.get_access_information(access_code)
    return {'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri,
            'refresh_token': access_information['refresh_token']}


if __name__ == '__main__':
    try:
        authenticate_reddit()
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
