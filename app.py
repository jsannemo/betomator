import datetime
import os
import urllib.parse

from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_login import login_required

import auth
import bets
import dashboard
import models
import scoreboard

app = Flask(__name__)
app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = "lumen"

app.config["SPLITWISE"] = {
    "consumer_key": os.environ["SPLITWISE_CLIENT"],
    "consumer_secret": os.environ["SPLITWISE_SECRET"],
    "base_url": "https://www.splitwise.com/api/v3.0/"
}
if app.config["ENV"] == "development":
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite"
    app.config["HOST"] = "http://127.0.0.1:5000"
    app.secret_key = "test secret key"
else:
    app.config["HOST"] = os.environ["HOST"]
    app.secret_key = os.environ["SECRET_KEY"]
    db_parsed_url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    username = db_parsed_url.username
    password = db_parsed_url.password
    database = db_parsed_url.path[1:]
    hostname = db_parsed_url.hostname
    db_url = f"postgresql+psycopg2://{username}:{password}@{hostname}/{database}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

app.config["SPLITWISE_ACCESS_GROUP"] = int(os.environ["SPLITWISE_ACCESS_GROUP"])
app.config["SPLITWISE_API_KEY"] = os.environ["SPLITWISE_API_KEY"]

app.register_blueprint(auth.blueprint)
app.register_blueprint(bets.blueprint)
app.register_blueprint(dashboard.blueprint)
app.register_blueprint(scoreboard.blueprint)

auth.init_app(app)
models.init_app(app)
bootstrap = Bootstrap(app)


@app.route("/help")
@login_required
def help():
    return render_template("help.html")


@app.route('/init-db')
def init():
    models.db.create_all()


@app.context_processor
def now():
    return {"now": datetime.datetime.now()}
