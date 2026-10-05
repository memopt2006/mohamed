# Results (walk-forward, 1-minute data 2025-10-01 → 2026-10-03)

35,232 fifteen-minute windows. Every number below is out of sample: each month
is predicted by a model trained only on earlier months (tests start Jan 2026,
26,496 windows). Features were chosen on data before 2026-05-04; **Jun–Oct 2026
is a holdout** scored once.

## Up/down calls

| Model | Hit rate | Most confident 25% | Most confident 10% |
|---|---|---|---|
| Always "Up" | 49.95% | – | – |
| Fade the last hour (old app rule) | 52.26% | 52.28% | 52.28% |
| Logistic, 9 features | 52.69% | 55.68% | 57.58% |
| LightGBM, 34 features | 52.95% | 56.07% | 56.45% |
| Ensemble | 53.28% | 56.28% | 57.66% |

Following any recent move loses (47–49%); BTC mean-reverts over 15 minutes.

## Deployed model (logistic, 10 features) by strength band

| Band (model's side probability) | Selection period | **Holdout Jun–Oct** |
|---|---|---|
| Strong (≥ 55%) | 56.8% (3,199) | **55.3% (2,853)** |
| Medium (53–55%) | 55.2% (3,425) | 52.2% (3,019) |
| Weak (< 53%) | 52.3% (7,872) | 49.9% (6,128) |

Strong calls by month (hit %, trades): Jan 58.8 (532), Feb 55.0 (555),
Mar 58.7 (624), Apr 57.9 (692), May 54.3 (796), Jun 54.1 (782),
Jul 55.6 (741), Aug 55.6 (693), Sep 57.1 (576).

Profit per $1 contract for Strong calls at a fixed entry price (holdout 55.3%):
+3.3¢ at 52¢, +1.3¢ at 54¢, about −0.7¢ at 56¢. **Whether this works depends
on the price Robinhood actually charges.** That's what the paper log measures.

Calibration: on the holdout the raw model is overconfident (log-odds slope
0.65), so the app shows confidence shrunk by 0.75.

## In-window fair value
- The random-walk formula with the 60-second settlement average is well
  calibrated (best volatility scale 0.95).
- Adding the pre-window model's log-odds improves it (log loss 0.4494 →
  0.4460 over 329,280 window-minutes). The pre-window signal keeps working
  through the window.
- In 12% of window-minutes the fitted fair value differs from the plain
  random-walk price by 5¢ or more.

## Live check and Prime tier (added 2026-10-04)
- First 54 live calls (Sat night to Sun morning): Strong 4/7, Medium 7/17,
  Weak 16/30. Far too few to judge. BTC climbed slowly all morning, which is
  the hardest case for a snap-back model.
- Live features match the research pipeline. The start price differed by up to
  about $12 when only one exchange's first minute had arrived, so calls now wait
  for both exchanges (with a fallback after 4 minutes).
- Breakdown of Strong calls, consistent in both the selection period and the
  holdout:

| Strong calls when… | Selection | Holdout |
|---|---|---|
| \|z_240\| ≥ 0.868 (big 4-hour move, top third) | 59.5% | 58.1% (n=1,149) |
| …and 18:00–05:59 UTC (2 PM–2 AM New York) | 62.0% | 62.8% (n=484) |
| other Strong calls | – | 53.4% |

- New tiers stored with each call: `prime+`, `prime`, `strong`, `medium`,
  `weak`. Only Prime is "Buy". The |z_240| cutoff came from the selection
  period. The time-of-day split was spotted with the holdout in view, so treat
  Prime ★ as promising, not proven, until live data confirms it.

## Second training year and new signals (added 2026-10-05)
Downloaded Oct 2024 – Sep 2025 (Coinbase + Bitstamp) and two years of
Binance.US BTC/USDT taker-buy volume.

- **Order flow (Binance.US): no help.** Following buy/sell pressure hit 49%;
  adding it to the model slightly lowered holdout results (Prime 57.7% vs
  58.1%). Binance.US trades only ~0.03 BTC/min, too thin to matter.
- **Interaction terms** (big-move × signals, evening × signals): within ±1.5
  points of the simple Prime filter. Not adopted.
- **2-year training** (same 10 features), holdout Jun–Oct 2026:

| | 1-year | 2-year |
|---|---|---|
| Log-loss gain | 9.4 bp | 11.2 bp |
| Calibration slope (1 = perfect) | 0.65 | 0.79 |
| Strong hit | 55.0% (2,864) | 56.5% (1,514) |
| Prime hit | 58.0% (1,142) | 58.8% (706) |
| Prime ★ hit | 62.8% (481) | 64.0% (308) |

- **Fresh-year check** (model trained on Oct 2025 – Oct 2026, scored on
  Oct 2024 – Sep 2025, 34,944 windows): Strong 55.2%, Prime ★ 56.5%,
  Prime 54.6%, Strong without big move 55.1%, Medium 51.4%, Weak 50.6%.
  **Strong ≈ 55% holds in all three periods.** The Prime/Prime ★ boost was
  mostly a 2026 effect.
- Deployed: the 2-year model (`fit_final.py`). All Strong-family calls are now
  "Buy" with price caps from conservative rates (★ 58% → 55¢, Prime 56% →
  53¢, Strong 55% → 52¢). The app's honesty shrink is now 0.8.

## Classic indicators (added 2026-10-05)
`research5.py` tested MACD (12/26/9 and 60/130/45, line and histogram),
Bollinger %B (20, 60), CCI (20, 60), VWAP distance (60, 240), Stochastic
%K/%D (14, 60), EMA slopes (20, 60) and trend efficiency (60, 240), with
2-year training and selection on data before 2026-06.

- Following any of them alone hit 47.7–48.7%, so fading them hits 51–52%:
  the same snap-back signal the model already has.
- Best addition (MACD histogram) improved selection log loss by 0.3 bp, below
  the 2 bp bar. **Nothing added.** The 10 live features already capture it.

## Live losing streak review (added 2026-10-05)
- Since the 2-year model went live, high-confidence calls went 0/9. All
  Strong-family calls since launch: 11/27 (41%).
- Not a bug: the live probabilities match an offline recomputation to 4
  decimals.
- The losses came in two one-way trends (a ~$1,100 fall overnight and a slow
  afternoon climb). The model kept betting on a snap-back at fresh 4-hour
  lows and highs.
- `research6.py`: trend guards don't help. After a losing call, the next
  same-direction Strong call wins *more* (57–59%), and calls during smooth
  one-way hours still win 55–58%. Strong calls at a fresh 4-hour extreme won
  56.0% / 56.2% / 57.9% in the three periods.
- Historical runs of consecutive Strong losses: 13 (2024–25), 7 (Jan–May
  2026), 9 (Jun–Oct 2026). Losing streaks this long are part of a 55% edge.
- Plan: keep paper trading to ~150 live Strong calls. If live is still below
  ~52% then, the model isn't working live and should be stopped.
