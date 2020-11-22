from flask import Blueprint, render_template
from flask_login import login_required

blueprint = Blueprint("scoreboard", __name__, url_prefix="/scoreboard")


@blueprint.route("/")
@login_required
def scoreboard():
    return render_template("scoreboard/scoreboard.html")
