"""Forward feature selection on the selection period only (data up to early May 2026)."""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import walk_forward, m_logit, logloss, FEATS, SMALL
warnings.filterwarnings('ignore')
df = load(sys.argv[1]); win = windows(df, build(df)); y = win['up'].values
def gain(cols):
    p = walk_forward(win, m_logit(cols)).values; m = ~np.isnan(p)
    return (logloss(y[m], np.full(m.sum(), y[m].mean())) - logloss(y[m], p[m])) * 1e4
base = gain(SMALL); print('SMALL', round(base, 1))
cur = list(SMALL)
for rnd in range(4):
    best = None
    for c in FEATS:
        if c in cur: continue
        g = gain(cur + [c])
        if best is None or g > best[1]: best = (c, g)
    print('round', rnd, 'best add', best[0], round(best[1], 1))
    if best[1] - base < 2: break
    cur.append(best[0]); base = best[1]
# also try dropping each
for c in list(cur):
    g = gain([x for x in cur if x != c]); print('drop', c, round(g - base, 1))
print(json.dumps(cur))
