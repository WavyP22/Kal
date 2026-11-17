# Kalshi Guard v3 — Android-friendly research prototype

**Read-only. No trades, no login, no automatic favorable-pick claims.**

## Quick start

1. Install Python 3.10+ on a computer.
2. Unzip this project and open a terminal in the folder.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.
5. Open the local address Streamlit prints. For Android, upload these files to a GitHub repository and deploy `app.py` at https://share.streamlit.io/ . Open the hosted URL on Android Chrome, then Add to Home screen.

## What works

- Attempts to retrieve open Kalshi public markets; reports network errors rather than inventing prices. Market matching is approximate and the paginated sample may miss NFL/NBA events.
- Downloads an evidence CSV template, validates evidence claim structure and freshness, and exports a blocker report.
- Generates two- and three-leg **hypothetical** combinations across distinct games from uploaded rows.
- Calculates central and conservatively stressed joint probability, break-even rate and hypothetical EV; exports CSV.
- Tests missing and stale evidence, unknown injuries, unconfirmed news, duplicate games, and probability errors.

## Limitations / safety

The app **does not** automatically fetch injury, suspension, lineup, or news feeds; it cannot authenticate user-entered source URLs or claims. It does not train or validate probability models, calculate actual correlations, fetch live combo RFQs, verify fees, or send background alerts. Quote inputs are hypothetical and reused for every scenario; do not interpret positive EV as an actual trading opportunity. A status of `CLAIMS PASS (UNVERIFIED)` is not evidence of independent verification. The application does not recommend trades or place orders.

Never upload passwords, API keys, or private account details. A public Streamlit deployment can expose your app and uploaded data to operational risk; use non-sensitive research data only.

## Test

`python -m unittest discover -v`
