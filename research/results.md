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
