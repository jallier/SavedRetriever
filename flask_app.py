from flask import Flask, render_template, url_for, request, flash, redirect
from flask_sqlalchemy import SQLAlchemy

from Resources.forms import SettingsForm

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

#import models so db knows where the models are
from Resources import models

@app.route("/")
def main():
    return render_template('index.html', posts={1, 2, 3, 4, 5})


@app.route("/settings", methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    if not form.validate_on_submit():
        flash("Please enter keys for required services")
    return render_template('settings.html', form=form)


if __name__ == "__main__":
    app.run()
