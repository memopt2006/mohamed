"""Stage 6: losing streaks in one-way trends. Do simple trend guards improve Strong calls?

Uses out-of-sample predictions: 2-year walk-forward (Jan-Oct 2026) and the fresh-year check
(model trained on Oct 2025-Oct 2026, scored on Oct 2024-Sep 2025).
Usage: python3 research6.py minutes_2y.pkl p_2y.pkl
"""
import sys, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import m_logit
from research2 import DEPLOY

warnings.filterwarnings('ignore')
df = load(sys.argv[1]); win = windows(df, build(df))
P = pd.read_pickle(sys.argv[2])['2y training']
fresh = pd.Series(m_logit(DEPLOY)(win[win.index >= '2025-10-01'], win[win.index < '2025-10-01']),
                  index=win.index[win.index < '2025-10-01'])
p = P.combine_first(fresh)
w = win.assign(p=p).dropna(subset=['p']).copy()
w['side'] = np.maximum(w.p, 1 - w.p); w['dir'] = np.where(w.p >= .5, 1, -1)
w['right'] = np.where(w.p >= .5, w.up == 1, w.up == 0)
# previous window (15 min earlier) facts known at the start of this window
prev = w.shift(1)
w['prev_same_dir_strong'] = (prev.side >= .55) & (prev.dir == w.dir)
w['prev_lost'] = ~prev.right.astype(bool)
w['against_1h'] = np.sign(w.ret_60) == -w.dir          # betting against the last hour's move
w['against_4h'] = np.sign(w.ret_240) == -w.dir
w['big_1h'] = np.abs(w.ret_60) / (w.rv_240 * np.sqrt(60)) >= 1.5   # last hour moved > 1.5 sigma
w['eff_60'] = (df['open'] - df['open'].shift(60)).abs().reindex(w.index) / \
              df['open'].diff().abs().rolling(60).sum().reindex(w.index)
w['trending'] = w.eff_60 >= w.eff_60.quantile(0.75)    # smooth one-way hour (top quarter)

periods = {'fresh 2024-25': w.index < '2025-10-01', 'Jan-May 2026': (w.index >= '2026-01-01') & (w.index < '2026-06-01'),
           'Jun-Oct 2026': w.index >= '2026-06-01'}
st = w.side >= .55
rules = {
    'all Strong (live rule)': st,
    'Strong, skip if previous same call lost': st & ~(w.prev_same_dir_strong & w.prev_lost),
    'Strong, skip if last hour >1.5 sigma move': st & ~w.big_1h,
    'Strong, skip smooth one-way hours': st & ~w.trending,
    'Strong, skip if both (prev lost OR trending)': st & ~((w.prev_same_dir_strong & w.prev_lost) | w.trending),
    '-- the skipped: previous same call lost': st & w.prev_same_dir_strong & w.prev_lost,
    '-- the skipped: smooth one-way hours': st & w.trending,
}
print(f"{'rule':48s}" + ''.join(f'{k:>22s}' for k in periods))
for name, m in rules.items():
    cells = []
    for k, pm in periods.items():
        s = m & pm; d = pm.sum() / 96
        cells.append(f"{w.right[s].mean()*100:5.1f}% ({s.sum()/d:4.1f}/d)")
    print(f'{name:48s}' + ''.join(f'{c:>22s}' for c in cells))
# how clustered are Strong losses? longest losing streak of consecutive Strong calls per period
for k, pm in periods.items():
    r = w[st & pm].right.values; streak = best = 0
    for x in r:
        streak = 0 if x else streak + 1; best = max(best, streak)
    print(f'{k}: longest run of consecutive Strong losses = {best}')
