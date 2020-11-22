import datetime

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import func, or_, and_
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
from wtforms import StringField, TextAreaField, SubmitField, FieldList, SelectField
from wtforms.fields.html5 import IntegerField, DateTimeLocalField
from wtforms.validators import DataRequired, NumberRange

import engine
import models
import payments
from models import Bet, transaction, db, Outcome, Bid, Contract

blueprint = Blueprint("bets", __name__, url_prefix="/bets")


def _my_bets(bets):
    return [bet for bet in bets if bet.owner == current_user]


@blueprint.route("/")
@login_required
def list_bets():
    bets = db.session.query(Bet).filter(or_(Bet.closed_at == None, Bet.closed_at >= datetime.datetime.now())).all()
    my_bets = _my_bets(bets)
    return render_template("bets/list.html", bets=bets, my_bets=my_bets)


@blueprint.route("/unresolved")
@login_required
def unresolved_bets():
    bets = db.session.query(Bet).filter(and_(Bet.resolved_at == None, Bet.closed_at <= datetime.datetime.now())).all()
    my_bets = _my_bets(bets)
    return render_template("bets/list.html", bets=bets, my_bets=my_bets)


@blueprint.route("/past")
@login_required
def past_bets():
    bets = db.session.query(Bet).filter(Bet.resolved_at.isnot(None)).all()
    my_bets = _my_bets(bets)
    return render_template("bets/list.html", bets=bets, my_bets=my_bets)


class CreateBetForm(FlaskForm):
    name = StringField("Title",
                       description="The bet formulated as a question, such as 'From what party is the next Swedish "
                                   "prime minister?'",
                       validators=[DataRequired()])
    description = TextAreaField("Description",
                                description="A description of the bet, including the rules on how the bet is resolved.",
                                validators=[DataRequired()])
    outcomes = FieldList(StringField("Name",
                                     [DataRequired()],
                                     description="Note: each outcome can be betted on for or against, so binary "
                                                 "questions should have a single outcome 'Yes'",
                                     ), min_entries=1, max_entries=10)
    submit_button = SubmitField("Create Bet")


@blueprint.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = CreateBetForm()
    if form.validate_on_submit():
        with transaction() as tx:
            bet = Bet(title=form.name.data, description=form.description.data, owner=current_user)
            tx.add(bet)
            for t in form.outcomes.entries:
                tx.add(Outcome(title=t.data, bet=bet))
        return redirect(url_for('bets.bet', bet_id=bet.bet_id))
    return render_template("bets/create.html", create_form=form)


def _bid_to_exposure_data(bid):
    return {"amount": bid.amount, "price": bid.price, "yes": bid.yes_bid,
            "cancel_link": url_for("bets.cancel_bid", bid_id=bid.bid_id)}


def _contract_to_exposure_data(type, price, amount):
    return {"amount": amount, "price": price, "yes": type}


def _outcome_data(bet):
    data = []
    for o in bet.outcomes:
        last_yes = db.session.query(Contract).filter_by(outcome=o, yes_contract=True).order_by(Contract.contract_id.desc()).first()
        yes_price = db.session.query(func.max(Bid.price)).filter_by(outcome=o, yes_bid=True).first()[0]
        no_price = db.session.query(func.max(Bid.price)).filter_by(outcome=o, yes_bid=False).first()[0]

        exposure = []
        for bid in db.session.query(Bid).filter_by(outcome=o, bidder=current_user).all():
            exposure.append(_bid_to_exposure_data(bid))
        contracts = db.session.query(Contract).filter_by(outcome=o, bidder=current_user).all()
        yes_contract_amounts = {}
        no_contract_amounts = {}
        for contract in contracts:
            contract_amounts = yes_contract_amounts if contract.yes_contract else no_contract_amounts
            contract_amounts[contract.price] = contract_amounts.setdefault(contract.price, 0) + contract.amount
        for price, amount in yes_contract_amounts.items():
            exposure.append(_contract_to_exposure_data(True, price, amount))
        for price, amount in no_contract_amounts.items():
            exposure.append(_contract_to_exposure_data(False, price, amount))
        exposure = list(sorted(exposure, key=lambda e: ("cancel_link" in e, e["yes"], e["price"])))
        data.append({"title": o.title, "id": o.outcome_id, "exposure": exposure,
                     "last_yes": last_yes.price if last_yes else None,
                     "yes_price": 100 - yes_price if yes_price else None,
                     "no_price": 100 - no_price if no_price else None
                     })
    return data


class ResolveForm(FlaskForm):
    resolve_time = DateTimeLocalField("Resolve Time",
                                      description="The time at which the bet should have been considered resolved. Any "
                                                  "contracts past this time is disregarded.",
                                      default=datetime.datetime.now(),
                                      validators=[DataRequired()],
                                      format='%Y-%m-%dT%H:%M')
    resolve_choice = SelectField("Resolved Outcome",
                                 description="The outcome that occured. If none of the outcomes occurred, select None.",
                                 default=0,
                                 coerce=int)
    submit_button = SubmitField("Resolve")

    def set_choices_for_bet(self, bet):
        self.resolve_choice.choices = [(o.outcome_id, o.title) for o in bet.outcomes] + [(0, "None")]


class CloseForm(FlaskForm):
    close_time = DateTimeLocalField("Close Time",
                                    description="The time at which the bet should close.",
                                    format='%Y-%m-%dT%H:%M',
                                    validators=[DataRequired()],
                                    default=datetime.datetime.now())
    submit_button = SubmitField("Schedule Close")


@blueprint.route("/<int:bet_id>")
@login_required
def bet(bet_id):
    bet = db.session.query(Bet).filter_by(bet_id=bet_id).first_or_404()
    print(bet.won_outcome_id)
    resolve_form = ResolveForm()
    close_form = CloseForm()
    resolve_form.set_choices_for_bet(bet)
    return render_template("bets/bet.html", bet=bet, outcomes=_outcome_data(bet), close_form=close_form,
                           resolve_form=resolve_form)


@blueprint.route("/<int:bet_id>/close", methods=["GET", "POST"])
@login_required
def close_bet(bet_id):
    bet = db.session.query(Bet).filter_by(bet_id=bet_id).first_or_404()
    if bet.owner != current_user:
        raise Forbidden
    close_form = CloseForm()
    if not bet.closed and close_form.validate_on_submit():
        time = close_form.close_time.data
        bet.closed_at = time
        db.session.commit()
    return redirect(url_for("bets.bet", bet_id=bet_id))


@blueprint.route("/<int:bet_id>/resolve", methods=["GET", "POST"])
@login_required
def resolve_bet(bet_id):
    with transaction() as tx:
        bet = tx.query(Bet).filter_by(bet_id=bet_id).first_or_404()
        if bet.owner != current_user:
            raise Forbidden
        resolve_form = ResolveForm()
        resolve_form.set_choices_for_bet(bet)
        if bet.closed and not bet.resolved and resolve_form.validate_on_submit():
            time = resolve_form.resolve_time.data
            bet.resolved_at = time
            choice = resolve_form.resolve_choice.data
            print(choice)
            bet.won_outcome_id = choice if choice else None
            payments.resolve_payment(tx, bet)
            print(bet.resolved_at)
        print(resolve_form.errors)
    return redirect(url_for("bets.bet", bet_id=bet_id))


class CreateBidForm(FlaskForm):
    dir = SelectField("Bet Type",
                      choices=["yes", "no"],
                      description="Whether you bet that the outcome happens (YES) or not (NO).",
                      validators=[DataRequired()])
    price = IntegerField("Price", render_kw={"min": 1, "max": 99},
                         validators=[NumberRange(min=1, max=99), DataRequired()])
    amount = IntegerField("Amount", render_kw={"min": 1, "max": 1000},
                          validators=[NumberRange(min=1, max=1000), DataRequired()])
    submit_button = SubmitField("Create Bid")


@blueprint.route("/outcome/<int:outcome>/<string:dir>/bid", methods=["POST", "GET"])
@login_required
def bid(outcome, dir):
    form = CreateBidForm()
    if dir != "yes" and dir != "no":
        raise BadRequest
    with models.transaction() as txn:
        outcome = txn.query(Outcome).filter_by(outcome_id=outcome).first_or_404()
        if outcome.bet.closed_at:
            raise BadRequest
        if form.validate_on_submit():
            engine.resolve_bet(txn, current_user, outcome, form.price.data, form.amount.data, form.dir.data == "yes")
            return redirect(url_for('bets.bet', bet_id=outcome.bet_id))
    return render_template("bets/bid.html", bet=outcome.bet, outcome=outcome, bid_form=form, dir=dir)


@blueprint.route("/bid/<int:bid_id>/cancel", methods=["POST", "GET"])
@login_required
def cancel_bid(bid_id):
    bid = db.session.query(Bid).filter_by(bid_id=bid_id).first_or_404()
    if bid.outcome.bet.resolved_at:
        raise BadRequest
    if bid.bidder != current_user:
        raise NotFound
    bet_id = bid.outcome.bet_id
    if request.method == "POST":
        db.session.delete(bid)
        db.session.commit()
    return redirect(url_for("bets.bet", bet_id=bet_id))
