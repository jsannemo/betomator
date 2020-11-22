from flask import Blueprint, render_template
from flask_login import login_required

blueprint = Blueprint("dashboard", __name__, url_prefix="/")


@blueprint.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")
