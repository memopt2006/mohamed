# BTC 15-minute research

Research behind the BTC 15m app (`dashboard/btc15.html`) for Robinhood's
"BTC 15 min" up/down prediction markets.

## Data
- A year (2025-10-01 to 2026-10-03) of 1-minute candles from **Coinbase** and
  **Bitstamp**, downloaded into Supabase (`research.btc_1m`) through `pg_net`
  (see `research.fetch_jobs`, `research.fire()`, `research.ingest()`).
- **Settlement proxy.** Robinhood settles on CF Benchmarks' BRTI averaged over
  the last 60 seconds. Coinbase and Bitstamp are both BRTI constituents, so:
  - target = average of the two exchanges' opens at the window start
  - settle = average typical price `(o+h+l+c)/4` of the final minute
- Exported with `research.export_compact()` and decoded by `decode.py`.

## Method
- `features.py` builds features known at the window start: returns and
  volatility-scaled moves over 15 min to 24 h, realized volatility, RSI, where
  the price sits in its 1 h / 4 h / 24 h range, the Coinbase–Bitstamp premium,
  volume, hour of day, and previous window results. Volume and the premium are
  lagged one minute so nothing from the future leaks in.
- `research.py` compares models **walk-forward**: each month is predicted by a
  model trained only on earlier months.
- `select_feats.py` picked the deployed features using data **before
  2026-05-04 only**. June–October is a holdout scored once.
- `research2.py` adds the profit simulation, strength bands, the in-window fair
  value model and the deployable coefficients.
- `gen_sql.py` turns the fitted model into the live Supabase function
  (`sql/btc15_v2.sql`).

## In-window fair value
At minute *t* of a window, with live price *P* and target *K*:

    z = ln(P/K) / (σ₁ₘ · √((14 − t) + 1/3))

where σ₁ₘ is the 1-minute volatility over the last hour and the 1/3 accounts for
the 60-second settlement average. A logistic model on `z`, `z·√t` and the
pre-window model's log-odds gives the probability that the window settles up,
which is the fair price of a Yes contract. The app recomputes it every
5 seconds from Coinbase's public ticker.

## Results
See `results.md`.
