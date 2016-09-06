import db_create
import os
from Resources import models
from flask_app import db
from sqlalchemy.exc import IntegrityError


def check_if_first_run():
    """
    Create the sqlite database and write the initial values the first time the app is run.
    First run status is determined by presence of app.db.
    """
    if not os.path.exists('app.db'):
        print("No db detected - creating...")
        _create_db()


def _create_db():
    """
    Function to create the db and write the values
    """
    db_create.main()
    print("Adding initial values...")
    new_user = models.User(username="admin", password="admin")
    try:  # Create a new default user
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        print("error creating db", e)
    user = models.User.query.get(1)
    settings = [models.Settings(key="color", value="blue", user_id=user.id),
                models.Settings(key="number_of_posts", value="20", user_id=user.id),
                models.Settings(key="run_on_schedule", value="True", user_id=user.id),
                models.Settings(key="cron_string", value="0 0 * * 0", user_id=user.id),
                models.Settings(key="save_comments", value="True", user_id=user.id),
                models.Settings(key="number_of_comments", value="5", user_id=user.id),
                models.Settings(key="reddit_refresh_token", value="", user_id=user.id)]

    for x in settings:
        db.session.add(x)
    try:
        db.session.commit()
        print("db created")
    except IntegrityError as e:
        db.session.rollback()
        print("Error creating db - %s", e)


if __name__ == "__main__":
    check_if_first_run()
