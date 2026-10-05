"""Stage 7: volume profile. Point of control (POC), value area (70% of volume), and the
volume at the current price, over the previous 4 h and 24 h, from Coinbase+Bitstamp 1-minute
volume spread across each minute's high-low range.

Usage: python3 research7.py minutes_2y.pkl p_2y.pkl
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import logloss, m_logit
from research2 import DEPLOY
from research3 import walk, report

warnings.filterwarnings('ignore')


def profile_feats(df, idx, look):
    """Features at each window start in idx from the previous `look` finished minutes."""
    p = df['open'].values; tp = df['typ'].values; v = df['vol'].values
    pos = df.index.get_indexer(idx)
    out = np.full((len(idx), 5), np.nan)
    for i, j in enumerate(pos):
        if j < look: continue
        tps, vs = tp[j - look:j], v[j - look:j]          # minutes before the window start
        if vs.sum() <= 0: continue
        lo, hi = tps.min(), tps.max()
        if hi <= lo: continue
        nb = 40
        h, edges = np.histogram(tps, bins=nb, range=(lo, hi), weights=vs)
        centers = (edges[:-1] + edges[1:]) / 2
        k = int(h.argmax()); poc = centers[k]
        # value area: grow out from the POC until 70% of volume is covered
        a = b = k; tot = h.sum(); cum = h[k]
        while cum < 0.7 * tot and (a > 0 or b < nb - 1):
            left = h[a - 1] if a > 0 else -1; right = h[b + 1] if b < nb - 1 else -1
            if right >= left: b += 1; cum += h[b]
            else: a -= 1; cum += h[a]
        val, vah = edges[a], edges[b + 1]
        price = p[j]; rng = hi - lo
        cb = min(max(int((price - lo) / rng * nb), 0), nb - 1)
        out[i] = [(price - poc) / rng,                               # distance to POC (range units)
                  1.0 if price > vah else (-1.0 if price < val else 0.0),   # above / below value area
                  (price - vah) / rng if price > vah else ((price - val) / rng if price < val else 0.0),
                  h[cb] / h.mean(),                                  # volume at current price (HVN > 1, LVN < 1)
                  (vah - val) / rng]                                 # width of the value area
    names = ['poc_dist', 'va_side', 'va_out', 'node_vol', 'va_width']
    return pd.DataFrame(out, index=idx, columns=[f'{n}_{look}' for n in names])


def main(path, pred_path):
    df = load(path)
    win = windows(df, build(df))
    for look in (240, 1440):
        win = win.join(profile_feats(df, win.index, look))
    VP = [c for c in win.columns if c.split('_')[-1] in ('240', '1440') and c.startswith(('poc', 'va_', 'node'))]
    win = win.dropna(subset=VP)
    sel = win[win.index < '2026-06-01']
    print('univariate checks before 2026-06 (share of windows that settled Up):')
    for c in VP:
        q = pd.qcut(sel[c].rank(method='first'), 5, labels=False)
        print(f'  {c:16s} quintiles low->high:', ' '.join(f'{x*100:4.1f}' for x in sel.groupby(q)['up'].mean()))

    def sel_gain(cols):
        pr = walk(win, cols, '2024-10-01'); m = pr.notna() & (win.index < '2026-06-01')
        y = win['up'][m].values
        return (logloss(y, np.full(len(y), y.mean())) - logloss(y, pr[m].values)) * 1e4, pr

    base, p0 = sel_gain(DEPLOY)
    print('\nbaseline selection gain', round(base, 1))
    cur, best_p = list(DEPLOY), p0
    for rnd in range(3):
        c, (g, pr) = max(((c, sel_gain(cur + [c])) for c in VP if c not in cur), key=lambda x: x[1][0])
        print(f'round {rnd}: best add {c} -> {g:.1f} (+{g-base:.1f})')
        if g - base < 2: break
        cur.append(c); base, best_p = g, pr
    print('chosen:', cur[len(DEPLOY):] or 'nothing')
    print(json.dumps(report('live 10 features', win, p0)))
    if cur != DEPLOY:
        print(json.dumps(report('10 + volume profile', win, best_p)))
        # fresh-year check: train on Oct 2025-Oct 2026, score Oct 2024-Sep 2025
        tr, te = win[win.index >= '2025-10-01'], win[win.index < '2025-10-01']
        for name, cols in [('live 10', DEPLOY), ('10 + VP', cur)]:
            pp = m_logit(cols)(tr, te); side = np.maximum(pp, 1 - pp); y = te['up'].values
            right = np.where(pp >= .5, y == 1, y == 0); s = side >= .55
            print(f'fresh year {name}: Strong {right[s].mean()*100:.1f}% (n={s.sum()})')
    # does the profile explain the falling-knife losses? Strong calls by value-area side
    pr = p0[p0.notna()]; w = win.loc[pr.index]
    side = np.maximum(pr, 1 - pr); right = np.where(pr >= .5, w.up == 1, w.up == 0)
    for c in ('va_side_240', 'va_side_1440'):
        for sv in (-1, 0, 1):
            m = (side >= .55) & (w[c] == sv)
            print(f'Strong calls with {c}={sv:+d}: {right[m].mean()*100:.1f}% (n={m.sum()})')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
