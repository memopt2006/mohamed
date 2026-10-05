"""Stage 8: Fibonacci retracement levels. Is price at a Fib level of the recent 4 h / 24 h range
any different from price at a similar range position that is not a Fib level?

Usage: python3 research8.py minutes_2y.pkl p_2y.pkl
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import logloss, m_logit
from research2 import DEPLOY
from research3 import walk, report

warnings.filterwarnings('ignore')
FIB = np.array([0.236, 0.382, 0.5, 0.618, 0.786])
CTRL = np.array([0.30, 0.44, 0.56, 0.70, 0.86])   # non-Fib control levels with similar spacing


def near(pos, levels, tol):
    return (np.abs(pos.values[:, None] - levels[None, :]) <= tol).any(axis=1)


df = load(sys.argv[1]); win = windows(df, build(df))
P = pd.read_pickle(sys.argv[2])['2y training']
fresh = pd.Series(m_logit(DEPLOY)(win[win.index >= '2025-10-01'], win[win.index < '2025-10-01']),
                  index=win.index[win.index < '2025-10-01'])
win['p'] = P.combine_first(fresh)
for look in (240, 1440):
    rp = win[f'rangepos_{look}']
    d = np.abs(rp.values[:, None] - FIB[None, :]).min(axis=1)
    win[f'fib_dist_{look}'] = d                                    # distance to nearest Fib level
    win[f'at_fib_{look}'] = near(rp, FIB, 0.02).astype(float)      # within 2% of the range
    win[f'at_ctrl_{look}'] = near(rp, CTRL, 0.02).astype(float)

# 1) Do Fib levels act as support/resistance? Compare the 15-minute move direction relative to the
#    last 15 min (did the move reverse?) at Fib levels vs control levels.
w = win.dropna(subset=['p'])
rev = np.sign(w['ret_15']) != np.where(w['up'] == 1, 1, -1)       # window went against the last 15 min
side = np.maximum(w.p, 1 - w.p); right = np.where(w.p >= .5, w.up == 1, w.up == 0)
print('share of windows that reversed the previous 15-min move:')
for look in (240, 1440):
    for name, col in [('at Fib level', f'at_fib_{look}'), ('at control level', f'at_ctrl_{look}')]:
        m = w[col] == 1
        print(f'  {look//60:>2}h range, {name:17s}: {rev[m].mean()*100:5.1f}% (n={m.sum()})')
print('Strong-call hit rate:')
for look in (240, 1440):
    for name, col in [('at Fib level', f'at_fib_{look}'), ('at control level', f'at_ctrl_{look}'), ('elsewhere', None)]:
        m = (side >= .55) & ((w[col] == 1) if col else ((w[f'at_fib_{look}'] == 0) & (w[f'at_ctrl_{look}'] == 0)))
        print(f'  {look//60:>2}h range, {name:17s}: {right[m].mean()*100:5.1f}% (n={m.sum()})')

# 2) Does adding Fib features improve the model? (selection period only, 2-year training)
FEAT = ['fib_dist_240', 'at_fib_240', 'fib_dist_1440', 'at_fib_1440']
def sel_gain(cols):
    pr = walk(win, cols, '2024-10-01'); m = pr.notna() & (win.index < '2026-06-01'); y = win['up'][m].values
    return (logloss(y, np.full(len(y), y.mean())) - logloss(y, pr[m].values)) * 1e4
base = sel_gain(DEPLOY)
print(f'\nbaseline selection gain {base:.1f}')
for c in FEAT:
    print(f'  + {c:14s} {sel_gain(DEPLOY + [c]) - base:+.1f} bp')
