# The Bet-O-Mator
The Bet-O-Mator is an open-source private betting market that you can host to bet on things with friends.
Its main feature is automatic synchronization with a Splitwise group for debts, used to handle payments of the resolved bets.

## Local Development
First, you need to create a Splitwise OAuth2 app and a group for testing.
The OAuth app should have `http://127.0.0.1:5000/login/callback` as its callback URL.

Then, configure the following variables in your environment:
```
export SPLITWISE_CLIENT=...
export SPLITWISE_SECRET=...
export SPLITWISE_ACCESS_GROUP=...
```

To run the development server, perform the following steps:
- Install Poetry
- Run `poetry install`
- Run `poetry shell`
- Run `FLASK_ENV=development flask db create`
- Run `FLASK_ENV=development flask run`

To wipe the test database, run 
`FLASK_ENV=development flask db destroy` followed by
`FLASK_ENV=development flask db create`.

