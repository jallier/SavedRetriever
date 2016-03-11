import praw


def reddit_oauth_wizard(access_token):
    CLIENT_ID = '_Nxh9h0Tys5KCQ'
    redirect_uri = 'http://127.0.0.1:5000/authorize_callback'

    r = praw.Reddit('Saved Retriever Installed by /u/fuzzycut')
    r.set_oauth_app_info(CLIENT_ID, '', redirect_uri)

    access_info = r.get_access_information(access_token)

    # user = r.get_me()
    # print(user.name)

    return access_info['refresh_token']
