# Kalshi Guard v5 — All Sports Discovery

Read-only Streamlit research dashboard. Uses Kalshi public API to discover Sports-category series and fetch open event markets. **Does not automatically recommend picks.** Sports discovery and market scan are bounded by user-selected limits; errors and incomplete coverage are shown. No account connection or trades.

## Deploy on your existing Streamlit Cloud app

1. Extract this ZIP and upload `app.py`, `discovery.py`, `engine.py`, `requirements.txt`, `test_discovery.py` to your existing GitHub repository, at the root. Overwrite old files when prompted.
2. Streamlit Cloud should redeploy from the repository. Main file path remains `app.py`.
3. Open the app, select **All-sports scan** and click **Scan Kalshi sports markets**.
4. Filter the results and download CSV. The other tabs support manual research only.

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest test_discovery -v
```


## Limits

Kalshi may change endpoint schema, categories, pagination, or access. A successful scan does not prove full market coverage. Missing prices are not fabricated. Injuries, lineups, news, calibrated probabilities and executable combo quotes are **not integrated**. Never treat a manually entered probability as independently validated.
