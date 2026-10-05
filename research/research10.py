"""Stage 10: free data that isn't BTC spot price.
  - OKX BTC perpetual futures: premium over spot (basis) and futures volume surges
  - ETH lead-lag: does ETH's last few minutes predict BTC's next 15?
  - News-time proxy: Strong calls in weekday windows at 8:30 AM ET and 2:00 PM ET (US data releases)
Same protocol: 2-year training, selection on data before 2026-06, then holdout and fresh-year checks.

Usage: python3 research10.py minutes_2y.pkl okx.pkl p_2y.pkl
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import logloss, m_logit
from research2 import DEPLOY
from research3 import walk, report

warnings.filterwarnings('ignore')


def okx_feats(df, ok):
    ok = ok.reindex(df.index)
    p = df['open']
    basis = (ok['basis'] / p * 1e4)                       # perp premium in basis points (minute-start prices)
    out = pd.DataFrame(index=df.index)
    out['basis'] = basis.ffill()
    out['basis_chg_15'] = (basis - basis.shift(15)).ffill()
    out['basis_dev_240'] = (basis - basis.rolling(240, min_periods=60).mean()).ffill()
    pv = ok['pv'].fillna(0).shift(1)                      # finished minutes only
    sv = df['vol'].shift(1)
    out['perp_vz_15'] = np.log1p(pv.rolling(15).sum()) - np.log1p(pv.rolling(1440).sum() / 96)
    out['perp_spot_ratio'] = np.log1p(pv.rolling(15).sum()) - np.log1p(sv.rolling(15).sum())
    le = np.log(ok['eth'].ffill())
    lb = np.log(p)
    for k in (1, 3, 5, 15):
        out[f'eth_ret_{k}'] = le - le.shift(k)
    # ETH move not explained by BTC's own move (residual), in volatility units
    rv = (lb.diff()).rolling(240).std()
    for k in (3, 15):
        out[f'eth_lead_{k}'] = ((le - le.shift(k)) - (lb - lb.shift(k))) / (rv * np.sqrt(k))
    return out


def main(px_path, okx_path, pred_path):
    df = load(px_path)
    ok = pd.read_pickle(okx_path)
    f = build(df).join(okx_feats(df, ok))
    win = windows(df, f)
    NEW = ['basis', 'basis_chg_15', 'basis_dev_240', 'perp_vz_15', 'perp_spot_ratio',
           'eth_ret_1', 'eth_ret_3', 'eth_ret_5', 'eth_ret_15', 'eth_lead_3', 'eth_lead_15']
    win = win.dropna(subset=NEW)
    sel = win[win.index < '2026-06-01']
    print('univariate before 2026-06 (share of windows that settled Up, by quintile low -> high):')
    for c in NEW:
        q = pd.qcut(sel[c].rank(method='first'), 5, labels=False)
        print(f'  {c:16s}', ' '.join(f'{x*100:4.1f}' for x in sel.groupby(q)['up'].mean()))

    def sel_gain(cols):
        pr = walk(win, cols, '2024-10-01'); m = pr.notna() & (win.index < '2026-06-01'); y = win['up'][m].values
        return (logloss(y, np.full(len(y), y.mean())) - logloss(y, pr[m].values)) * 1e4, pr

    base, p0 = sel_gain(DEPLOY)
    print(f'\nbaseline selection gain {base:.1f}')
    cur, best_p = list(DEPLOY), p0
    for rnd in range(3):
        c, (g, pr) = max(((c, sel_gain(cur + [c])) for c in NEW if c not in cur), key=lambda x: x[1][0])
        print(f'round {rnd}: best add {c} -> {g:.1f} (+{g-base:.1f})')
        if g - base < 2: break
        cur.append(c); base, best_p = g, pr
    print('chosen:', cur[len(DEPLOY):] or 'nothing')
    print(json.dumps(report('live 10 features', win, p0)))
    if cur != DEPLOY:
        print(json.dumps(report('10 + new', win, best_p)))
        tr, te = win[win.index >= '2025-10-01'], win[win.index < '2025-10-01']
        for name, cols in [('live 10', DEPLOY), ('10 + new', cur)]:
            pp = m_logit(cols)(tr, te); s = np.maximum(pp, 1 - pp) >= .55; y = te['up'].values
            right = np.where(pp >= .5, y == 1, y == 0)
            print(f'fresh year {name}: Strong {right[s].mean()*100:.1f}% (n={s.sum()})')

    # news-time proxy: weekday windows starting 8:30 or 14:00 New York time
    P = pd.read_pickle(pred_path)['2y training']
    fresh = pd.Series(m_logit(DEPLOY)(win[win.index >= '2025-10-01'], win[win.index < '2025-10-01']),
                      index=win.index[win.index < '2025-10-01'])
    w = win.assign(p=P.combine_first(fresh)).dropna(subset=['p'])
    ny = w.index.tz_convert('America/New_York')
    news = (ny.dayofweek < 5) & (((ny.hour == 8) & (ny.minute == 30)) | ((ny.hour == 14) & (ny.minute == 0)))
    side = np.maximum(w.p, 1 - w.p); right = np.where(w.p >= .5, w.up == 1, w.up == 0); st = side >= .55
    move = (w.S - w.K).abs()
    print(f'\nnews-time windows: median |move| ${move[news].median():.0f} vs ${move[~news].median():.0f} elsewhere')
    print(f'Strong calls in news-time windows: {right[st & news].mean()*100:.1f}% (n={(st & news).sum()})')
    print(f'Strong calls elsewhere:            {right[st & ~news].mean()*100:.1f}% (n={(st & ~news).sum()})')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
