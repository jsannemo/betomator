from flask import Blueprint, url_for, request, redirect, current_app, session, render_template
from flask_login import LoginManager, login_user
from flask_oauthlib.client import OAuth, OAuthException

import models
from models import User, db

blueprint = Blueprint("auth", __name__, url_prefix="/account")
oauth = OAuth()
_login_manager = LoginManager()
_splitwise = oauth.remote_app(
    "splitwise",
    access_token_url="https://secure.splitwise.com/oauth/token",
    authorize_url="https://secure.splitwise.com/oauth/authorize",
    app_key="SPLITWISE"
)


def init_app(app):
    oauth.init_app(app)
    _login_manager.init_app(app)


@_login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter_by(user_id=user_id).first()


@blueprint.route("/login")
def login():
    return _splitwise.authorize(
        callback=current_app.config["HOST"] + url_for("auth.callback"))


def _create_or_sign_in(username, name, email):
    with models.transaction() as tx:
        user = tx.query(User).filter_by(username=username).first()
        if not user:
            user = User(username=username, name=name, email=email)
            tx.add(user)
    login_user(user)


@blueprint.route("/login/callback")
def callback():
    next_url = request.args.get("next") or url_for('dashboard.dashboard')
    try:
        resp = _splitwise.authorized_response()
        if not resp or "access_token" not in resp:
            return redirect(next_url)
    except OAuthException as e:
        current_app.logger.info("Failure in Splitwise auth resonse: %s (%s)", e, e.data)
        return redirect(next_url)
    session["splitwise_token"] = (resp["access_token"], "")

    for group in _splitwise.get("get_groups", content_type="application/json").data["groups"]:
        if group["id"] == current_app.config["SPLITWISE_ACCESS_GROUP"]:
            break
    else:
        return redirect(url_for("auth.unauthorized"))
    user_data = _splitwise.get("get_current_user", content_type="application/json").data["user"]
    username = f"splitwise:{user_data['id']}"
    name = f"{user_data['first_name']} {user_data['last_name']}"
    email = user_data["email"]
    _create_or_sign_in(username, name, email)
    return redirect(next_url)


@blueprint.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html")


@_splitwise.tokengetter
def _get_splitwise_token():
    return session.get("splitwise_token")


_login_manager.login_view = "/account/login"
