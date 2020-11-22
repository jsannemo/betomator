from models import Contract, Bid


def resolve_bet(txn, bidder, outcome, price, amount, yes_dir):
    matching_bids = [b for b in outcome.bids if b.yes_bid != yes_dir and b.price >= 100 - price]
    matching_bids = list(sorted(matching_bids, key=lambda b: (-b.price, b.bid_id)))
    while matching_bids and amount:
        bid = matching_bids.pop(0)

        shares_matched = min(amount, bid.amount)
        amount -= shares_matched

        c1 = Contract(outcome=outcome, bidder=bidder, price=100 - bid.price, amount=shares_matched,
                      yes_contract=yes_dir)
        c2 = Contract(outcome=outcome, bidder=bid.bidder, price=bid.price, amount=shares_matched,
                      yes_contract=not yes_dir)
        if shares_matched == bid.amount:
            txn.delete(bid)
        else:
            bid.amount -= shares_matched
        txn.add(c1)
        txn.add(c2)
    if amount:
        existing = txn.query(Bid).filter_by(bidder=bidder, outcome=outcome, price=price, yes_bid=yes_dir).first()
        if existing:
            existing.amount += amount
            existing.save()
        else:
            bid = Bid(outcome=outcome, bidder=bidder, price=price, amount=amount, yes_bid=yes_dir)
            txn.add(bid)
