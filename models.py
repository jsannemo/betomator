import datetime
from contextlib import contextmanager

from flask.cli import AppGroup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


@contextmanager
def transaction():
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String)
    email = db.Column(db.String, nullable=False)
    bets = db.relationship("Bet", backref="owner", lazy=True)
    bids = db.relationship("Bid", backref="bidder", lazy=True)
    contract = db.relationship("Contract", backref="bidder", lazy=True)

    def get_id(self):
        return f"{self.user_id}"

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True


class Bet(db.Model):
    bet_id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    outcomes = db.relationship("Outcome", backref="bet", foreign_keys="Outcome.bet_id")
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    closed_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    payment_synced_at = db.Column(db.DateTime)
    won_outcome_id = db.Column(db.Integer, db.ForeignKey("outcome.outcome_id", ondelete="CASCADE", use_alter=True),
                            nullable=True)

    @property
    def closed(self):
        return self.closed_at and self.closed_at <= datetime.datetime.now()

    @property
    def resolved(self):
        return self.resolved_at is not None


class Outcome(db.Model):
    outcome_id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer, db.ForeignKey("bet.bet_id"), nullable=False)
    title = db.Column(db.String, nullable=False)
    bids = db.relationship("Bid", backref="outcome")
    contracts = db.relationship("Contract", backref="outcome")
    won_bets = db.relationship("Bet", backref="won_outcome", foreign_keys="Bet.won_outcome_id")


class Bid(db.Model):
    bid_id = db.Column(db.Integer, primary_key=True)
    outcome_id = db.Column(db.Integer, db.ForeignKey("outcome.outcome_id"), nullable=False)
    bidder_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    yes_bid = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())


class Contract(db.Model):
    contract_id = db.Column(db.Integer, primary_key=True)
    outcome_id = db.Column(db.Integer, db.ForeignKey("outcome.outcome_id"), nullable=False)
    bidder_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    yes_contract = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())


_db_cli = AppGroup('db')


@_db_cli.command('create')
def _create_db():
    db.create_all()


@_db_cli.command('destroy')
def _destroy_db():
    db.drop_all()


def init_app(app):
    db.init_app(app)
    app.cli.add_command(_db_cli)
