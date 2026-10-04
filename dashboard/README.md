# BTC 15m paper-trading panel

`btc15.html` shows the live BTC 15-minute "fade" call from Signal Desk
(Supabase project `crypto-signal-alerts`), a scorecard, and a box to log the
Robinhood contract price you saw for each window.

## Deploy
1. Put `btc15.html` next to `index.html` in the dashboard folder.
2. Redeploy that folder to Vercel (stocks-crypto project).
3. Open `stocks-crypto-eta.vercel.app/btc15.html` and bookmark it.

## Install as an app
- iPhone: open the site in Safari → Share → Add to Home Screen.
- Android: open it in Chrome → ⋮ menu → Add to Home screen / Install app.

## Use
- Each window: read the call, open Robinhood's BTC 15 min market for the same
  window, and enter the price for the called side in cents (e.g. `52`).
- After 1–2 weeks with 100+ priced trades, check the paper profit before
  trading real money.

## Backend
- Cron `btc15-paper-signals` (`2-59/5 * * * *`) logs a call at each window start
  and settles it at window end in `btc15_signals`.
- `btc15_scorecard` view: hit rate and paper P&L by strength.
- The page writes only through `rpc/btc15_set_price`.
