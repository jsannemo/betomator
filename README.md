# The Bet-O-Mator
The Bet-O-Mator is an open-source private betting market that you can host to bet on things with friends.
Its main feature is automatic synchronization with a Splitwise group for debts, used to handle payments of the resolved bets.

## Local Development
First, you need to create a Splitwise OAuth2 app and a group for testing.
The OAuth app should have `http://127.0.0.1:5000/login/callback` as its callback URL.

Then, create a configuration file `.env` containing
```
SPLITWISE_CLIENT=<YOUR SPLITWISE OAUTH CLIENT ID>
SPLITWISE_SECRET=<YOUR SPLITWISE OAUTH SECRET>
SPLITWISE_ACCESS_GROUP=<YOUR SPLITWISE GROUP>
SPLITWISE_API_KEY=<YOUR SPLITWISE API KEY>
HOST=http://127.0.0.1:5000
SECRET_KEY=very secret key
SQLALCHEMY_DATABASE_URI=sqlite:///example.sqlite
FLASK_ENV=development
```

To run the development server, perform the following steps:
- Install Poetry
- Install the Heroku CLI
- Run `poetry install`
- Run `poetry shell`
- Run `heroku local release`
- Run `heroku local`

To wipe the test database, run `FLASK_ENV=development flask db destroy`.

