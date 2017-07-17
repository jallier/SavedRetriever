import datetime

from flask_app import db
from flask_login import UserMixin


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(14), unique=True, index=True)
    permalink = db.Column(db.String(64), unique=True)
    type = db.Column(db.String(10))
    title = db.Column(db.String(255))
    body_content = db.Column(db.Text)
    summary = db.Column(db.Text)
    comments = db.Column(db.Text)
    date_posted = db.Column(db.DateTime)
    date_downloaded = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))

    def __init__(self, **kwargs):
        super(Post, self).__init__(**kwargs)
        self.date_downloaded = datetime.datetime.utcnow()

    def __repr__(self):
        return '<Post %s>' % self.permalink


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    posts = db.relationship('Post', lazy='dynamic', backref='author')

    def __repr__(self):
        return '<Author %s>' % self.username


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(32))
    file_path = db.Column(db.String(255), index=True, unique=True)
    #Add in fk relationship for posts

    def __repr__(self):
        return '<FilePath %s>' % self.file_path


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    password = db.Column(db.String(64))
    authenticated = db.Column(db.Boolean, default=False)
    settings = db.relationship("Settings", backref='user', lazy='dynamic')

    def get_id(self):
        return self.username

    def is_authenticated(self):
        return self.authenticated

    def is_anonymous(self):
        return False

    def is_active(self):
        return True

    def __repr__(self):
        return "<User {}>".format(self.username)


class Settings(db.Model):
    """
     setting_type is int, where
     0 = String
     1 = boolean
     2 = Integer
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    value = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Setting {}:{}>'.format(self.key, self.value)
