# Kalshi Guard v7 — local-day sports research

Deploy `app.py` in Streamlit Community Cloud. Upload all files in this ZIP to the repository root, replacing matching files. Run `pip install -r requirements.txt` and `streamlit run app.py` locally.

## Changes
- Today (default), Tomorrow and Choose a date, based on a manually selected time zone (Eastern default).
- Only markets with an explicit timezone-aware `scheduled_start_time` or event `start_time` are included in date-filtered plays and combos. Markets without these fields appear under Unverified start times. Kalshi may not provide these fields for many or most markets, so **Today's Plays may be empty even when sports markets are active**.
- Sport/league filters; separate market details; synthetic 2–6 pick same-day cross-event combinations.

## Critical limitations
- Game start time is **not** inferred from market closing or settlement times. A present start field is not independently validated against official sports schedules.
- Market prices are not model-derived win probabilities. Combo multiplication assumes independence and is NOT an executable Kalshi quote. There is no actual combo trade verification, injury/news feed, profitability verification, or trade placement.
- Scan is bounded by pagination/series caps; incomplete coverage is possible. Device timezone is NOT automatically detected; select it manually in the sidebar.
- If no games appear, inspect Unverified start times. Never assume an empty Today tab means there are no games today.

Run tests: `python -m unittest discover -v`.

## v7.1 Game start schedule improvement
When Kalshi doesn't expose a timezone-aware scheduled game start, the app attempts to cross-check NBA, WNBA, CBB, WCBB, NFL, NCAAF, MLB, NHL and MLS games against ESPN's public scoreboard. It requires a unique matchup with **both complete team names** present in the Kalshi event/title fields. Ambiguous or unsupported games stay in Unverified Start Times. ESPN's endpoint is unofficial and may be unavailable; no market close time is substituted. The date filter uses the selected time zone. This is not a guarantee of complete coverage or live deployment.
