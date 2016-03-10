from flask_app import db


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permalink = db.Column(db.String(64), index=True, unique=True)
    title = db.Column(db.String(255))
    body_content = db.Column(db.String(10000))
    date = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))

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
    file_path = db.Column(db.String(255), index=True, unique=True)
    #Add in fk relationship for posts

    def __repr__(self):
        return '<FilePath %s>' % self.file_path


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(32), unique=True)
    setting_value = db.Column(db.String(128))
    setting_type = db.Column(db.Integer)

    def __repr__(self):
        return '<Setting %s>' % self.setting_name
