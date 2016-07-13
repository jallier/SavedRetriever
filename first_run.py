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
    settings = [models.Settings(setting_name="color", setting_value="blue", setting_type=0),
                models.Settings(setting_name="number_of_posts", setting_value=20, setting_type=2),
                models.Settings(setting_name="run_on_schedule", setting_value="True", setting_type=1),
                models.Settings(setting_name="cron_string", setting_value="0 0 * * 0", setting_type=0),
                models.Settings(setting_name="save_comments", setting_value="True", setting_type=1),
                models.Settings(setting_name="number_of_comments", setting_value=5, setting_type=2),
                models.Settings(setting_name="reddit_refresh_token", setting_value="", setting_type=0)]

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
