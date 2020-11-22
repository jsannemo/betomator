import datetime
import json

from flask import current_app

from auth import oauth

_splitwise = oauth.remote_app(
    "splitwise2",
    access_token_url="https://secure.splitwise.com/oauth/token",
    authorize_url="https://secure.splitwise.com/oauth/authorize",
    app_key="SPLITWISE"
)


@_splitwise.tokengetter
def _get_splitwise_token():
    return current_app.config["SPLITWISE_API_KEY"]


def _dec(amount):
    amount = str(amount)
    while len(amount) < 3:
        amount = "0" + amount
    return amount[:-2] + "." + amount[-2:]


def resolve_payment(txn, bet):
    if not bet:
        return
    if not bet.resolved_at:
        return
    if bet.payment_synced_at:
        return

    tot_shares = 0
    pay = {}
    for o in bet.outcomes:
        for c in o.contracts:
            if c.created_at > bet.resolved_at:
                continue
            bidder_id = int(c.bidder.username.split(":")[1])
            if bidder_id not in pay: pay[bidder_id] = [0, 0]

            tot_shares += c.amount * c.price
            pay[bidder_id][0] += c.amount * c.price
            if (o == bet.won_outcome) == c.yes_contract:
                pay[bidder_id][1] += c.amount

    assert tot_shares % 100 == 0
    expense = {
        "cost": _dec(tot_shares),
        "description": bet.title,
        "payment": False,
        "group_id": current_app.config["SPLITWISE_ACCESS_GROUP"],
        "currency_code": "SEK",
        "details": f"BET:{bet.bet_id}"
    }
    for i, (user, amounts) in enumerate(pay.items()):
        expense[f"users__{i}__paid_share"] = _dec(amounts[0])
        expense[f"users__{i}__owed_share"] = _dec(amounts[1] * 100)
        expense[f"users__{i}__user_id"] = user
    response = _splitwise.post("create_expense", data=json.dumps(expense), format="json",
                               content_type="application/json").data
    if "expenses" in response:
        bet.payment_synced_at = datetime.datetime.now()
