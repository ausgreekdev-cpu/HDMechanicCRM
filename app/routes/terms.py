from flask import Blueprint, render_template

bp = Blueprint("terms", __name__)


@bp.route("/terms")
def terms_of_service():
    return render_template("terms.html")


@bp.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")


@bp.route("/refund")
def refund_policy():
    return render_template("refund.html")
