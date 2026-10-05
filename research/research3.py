"""Stage 3: does a second year of training data or Binance.US order flow improve the model?

Usage: python3 research3.py minutes_2y.pkl flow.pkl
Test months: 2026-01 .. 2026-10 (walk-forward, monthly refits), same as the 1-year study.
Feature choices use data before 2026-06 only; Jun-Oct 2026 stays the holdout.
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import m_logit, logloss
from research2 import DEPLOY

warnings.filterwarnings('ignore')
HOLD = '2026-06-01'
Z_CUT = 0.868   # |z_240| cutoff for the Prime tier (from the selection period of the 1-year study)


def flow_feats(df, flow):
    fl = flow.reindex(df.index)
    v = fl['v'].fillna(0).shift(1)            # minute T's volume isn't known at T
    t = fl['tbv'].fillna(0).shift(1)
    out = pd.DataFrame(index=df.index)
    for k in (5, 15, 60):
        sv, st = v.rolling(k).sum(), t.rolling(k).sum()
        out[f'imb_{k}'] = ((2 * st - sv) / sv.replace(0, np.nan)).fillna(0)
    day = v.rolling(1440).sum() / 96
    out['cvd_15'] = ((2 * t - v).rolling(15).sum() / day.replace(0, np.nan)).fillna(0)
    out['bu_vz'] = np.log1p(v.rolling(15).sum()) - np.log1p(day)
    return out


def walk(win, cols, train_from, test_from='2026-01-01'):
    months = win.index.to_period('M')
    preds = pd.Series(np.nan, index=win.index)
    for m in sorted(months[win.index >= test_from].unique()):
        tr = (months < m) & (win.index >= train_from)
        te = months == m
        preds[te] = m_logit(cols)(win[tr], win[te])
    return preds


def report(name, win, p):
    ok = p.notna()
    y = win['up'][ok].values; pp = p[ok].values
    side = np.maximum(pp, 1 - pp); right = np.where(pp >= .5, y == 1, y == 0)
    hold = (win.index[ok] >= HOLD)
    big = np.abs(win['z_240'][ok].values) >= Z_CUT
    r = {'model': name}
    for per, m in [('sel', ~hold), ('hold', hold)]:
        base = logloss(y[m], np.full(m.sum(), y[m].mean()))
        r[f'{per}_gain_bp'] = round((base - logloss(y[m], pp[m])) * 1e4, 1)
        s = m & (side >= .55)
        r[f'{per}_strong'] = f"{right[s].mean()*100:.1f}% ({s.sum()})"
        pr = s & big
        r[f'{per}_prime'] = f"{right[pr].mean()*100:.1f}% ({pr.sum()})"
    return r


def main(px_path, flow_path):
    df = load(px_path)
    f = build(df)
    flow = pd.read_pickle(flow_path)
    f = f.join(flow_feats(df, flow))
    win = windows(df, f)
    print('windows', len(win), win.index.min(), win.index.max())
    FLOW = ['imb_5', 'imb_15', 'imb_60', 'cvd_15', 'bu_vz']
    # univariate check of the flow signal on the selection period
    sel = win[win.index < HOLD]
    for c in FLOW:
        s = np.sign(sel[c]); hit = ((s > 0) == (sel['up'] == 1))[s != 0]
        print(f'follow {c}: {hit.mean()*100:.2f}% (n={len(hit)})')
    res = [
        report('10 features, 1y training', win, walk(win, DEPLOY, '2025-10-01')),
        report('10 features, 2y training', win, walk(win, DEPLOY, '2024-10-01')),
        report('10 + flow, 2y training', win, walk(win, DEPLOY + FLOW, '2024-10-01')),
        report('10 + imb_15, 2y training', win, walk(win, DEPLOY + ['imb_15'], '2024-10-01')),
    ]
    for r in res:
        print(json.dumps(r))
    return win


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
