from flask import Flask, render_template, url_for, request

app = Flask(__name__)


@app.route("/")
def main():
    return render_template('index.html', posts={1, 2, 3, 4, 5})


@app.route("/settings")
def settings():
    return render_template('settings.html')


if __name__ == "__main__":
    app.run()
