import db_create
import os
from Resources import models
from flask_app import db
from sqlalchemy.exc import IntegrityError


def check_if_first_run():
    """
    Create the sqlite database and write the initial values the first time the app is run.
    First run status is determined by presence of app.db.
    :return:
    """
    if not os.path.exists('app.db'):
        print("No db detected - creating...")
        _create_db()


def _create_db():
    """
    Function to create the db and write the values
    :return:
    """
    db_create.main()
    print("Adding initial values...")
    settings = []
    settings.append(models.Settings(setting_name="color", setting_value="blue", setting_type=0))
    settings.append(models.Settings(setting_name="number_of_posts", setting_value=20, setting_type=2))
    settings.append(models.Settings(setting_name="schedule_hour", setting_value=20, setting_type=2))
    settings.append(models.Settings(setting_name="schedule_min", setting_value=5, setting_type=2))
    settings.append(models.Settings(setting_name="number_of_comments", setting_value=5, setting_type=2))
    settings.append(models.Settings(setting_name="save_comments", setting_value="True", setting_type=1))

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
