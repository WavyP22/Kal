# Kalshi Guard v7.2 — clearer labels and safer scanning

## Improvements
- Spaces Kalshi requests; retries HTTP 429 with a delay and stops the scan if throttling continues.
- Prioritizes recognizable sports leagues rather than scanning the first arbitrary series.
- Caches market scans for 10 minutes and schedule matching for 15 minutes.
- Shows how many markets match the selected day, have unknown start times, or start on other dates.
- Renames confusing settings and adds hover-help bubbles.
- Keeps technical API errors behind an expandable section.

## Important limits
- The app still does not independently estimate win probabilities or verify injury news.
- Grouped picks are NOT actual executable Kalshi combo quotes. Payouts are synthetic and exclude fees.
- Kalshi may still rate-limit requests. A scan can still be incomplete.
- The game schedule matcher is conservative and may miss legitimate games.

## Install
Upload all files from the ZIP to the repository root and replace matching files. Keep `app.py` as the Streamlit entry point.
