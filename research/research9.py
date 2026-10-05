"""Stage 9: real profit against Polymarket's BTC 15-minute up/down prices (Jun-Oct 2026).

For each window we take the market's Up price at the moment our call is usable (~3 minutes in),
our fair value at that moment (pre-window model + live distance from target), and Polymarket's
actual resolution. Questions:
  1. Is the market itself well calibrated?
  2. Does our model add information beyond the market price?
  3. What would trading the gap have earned after spread and fees?

Usage: python3 research9.py minutes.pkl p_2y.pkl model.json pm_dump1.txt [pm_dump2.txt ...]
"""
import sys, re, json, warnings
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from features import load, build, windows, W

warnings.filterwarnings('ignore')


def read_pm(files):
    rows = {}
    for path in files:
        s = open(path).read()
        for m in re.finditer(r'"x\\?":\\?"(\d+)\|(up|down|)\|(\d*)\|([^"\\]*)', s):
            ts = pd.Timestamp(int(m.group(1)), unit='s', tz='UTC')
            pts = [(int(a), float(b)) for a, b in (x.split(':') for x in m.group(4).split(';') if x)]
            rows[ts] = (m.group(2), float(m.group(3) or 0), pts)
    return rows


def price_at(pts, sec):
    """last market price at or before `sec` seconds after the window start (None if none in the last 90 s)"""
    best = None
    for t, p in pts:
        if t <= sec and t > sec - 90:
            best = p
    return best


def main(px_path, pred_path, model_path, pm_files):
    df = load(px_path); f = build(df); win = windows(df, f)
    pre = pd.read_pickle(pred_path)['2y training']
    iw = json.load(open(model_path))['deploy_inwindow']
    a, bz, bpre, bzt = iw['intercept'], *iw['coef']
    pm = read_pm(pm_files)
    print('Polymarket windows loaded:', len(pm))
    out = []
    for ts, (outcome, vol, pts) in pm.items():
        if ts not in win.index or ts not in pre.index or not outcome or np.isnan(pre[ts]):
            continue
        for t_min in (3, 5, 8):
            mp = price_at(pts, t_min * 60)
            if mp is None or not (0.02 < mp < 0.98):
                continue
            P = df['open'].get(ts + pd.Timedelta(minutes=t_min)); K = df['open'].get(ts); rv = win.at[ts, 'rv_60']
            if P is None or K is None or not rv:
                continue
            rem = (W - 1 - t_min) + 1 / 3
            z = np.log(P / K) / (rv * np.sqrt(rem))
            lpre = np.log(pre[ts] / (1 - pre[ts]))
            fair = 1 / (1 + np.exp(-(a + bz * z + bpre * lpre + bzt * z * np.sqrt(t_min))))
            fair_rw = norm.cdf(z / 0.95)                              # same, without our model's view
            out.append(dict(ts=ts, t=t_min, mkt=mp, fair=fair, fair_rw=fair_rw, p_pre=pre[ts],
                            up=1 if outcome == 'up' else 0, vol=vol))
    d = pd.DataFrame(out)
    print('rows', len(d), 'windows', d.ts.nunique())
    lg = lambda x: np.log(np.clip(x, 1e-4, 1 - 1e-4) / (1 - np.clip(x, 1e-4, 1 - 1e-4)))
    for t_min in (3, 5, 8):
        x = d[d.t == t_min]
        # 1) calibration of the market: bucket market price vs actual Up rate
        b = pd.cut(x.mkt, [0, .3, .4, .45, .5, .55, .6, .7, 1])
        cal = x.groupby(b).agg(mkt=('mkt', 'mean'), actual=('up', 'mean'), n=('up', 'size')).round(3)
        # 2) does our view add information beyond the market? logistic regression on both log-odds
        X = np.column_stack([lg(x.mkt), lg(x.fair) - lg(x.fair_rw)])   # market, and our model's extra view
        lr = LogisticRegression(C=1e6).fit(X, x.up)
        # 3) trading: buy the side where our fair value beats the market by >= edge, pay cost per contract
        res = []
        for edge in (0.02, 0.04, 0.06, 0.08):
            for cost in (0.01, 0.02, 0.03):
                buy_up = x.fair - x.mkt >= edge + cost
                buy_dn = x.mkt - x.fair >= edge + cost
                pnl = np.concatenate([(x.up[buy_up] - (x.mkt[buy_up] + cost)).values,
                                      ((1 - x.up[buy_dn]) - (1 - x.mkt[buy_dn] + cost)).values])
                res.append((edge, cost, len(pnl), round(len(pnl) / x.ts.nunique() * 96, 1),
                            round(float(pnl.mean()) * 100, 2) if len(pnl) else None,
                            round(float(pnl.std() / np.sqrt(len(pnl))) * 100, 2) if len(pnl) > 1 else None))
        print(f'\n===== entry at minute {t_min} ({len(x)} windows) =====')
        print('market calibration (price bucket -> actual Up rate):'); print(cal.to_string())
        print(f'logit(Up) = {lr.intercept_[0]:.3f} + {lr.coef_[0][0]:.3f}*logit(market) + {lr.coef_[0][1]:.3f}*our_extra_view')
        print('trading the gap  (edge, cost/contract, trades, trades/day, avg P&L cents, std err cents):')
        for r in res:
            print('  ', r)
    d.to_pickle(px_path.replace('.pkl', '_pm.pkl'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
