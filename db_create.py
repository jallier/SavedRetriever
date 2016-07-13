import os.path
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
from flask_app import db
from migrate.versioning import api


def main():
    """
    Code from Miguel Grinberg's Flask tutorial
    :return:
    """
    db.create_all()
    if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
        api.create(SQLALCHEMY_MIGRATE_REPO, 'database repository')
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    else:
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version(SQLALCHEMY_MIGRATE_REPO))


if __name__ == "__main__":
    main()
