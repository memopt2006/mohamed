"""Stage 5: do classic indicators (MACD, Bollinger %B, VWAP distance, Stochastic, CCI, Williams %R,
EMA slopes, ADX-style trend strength) add anything to the deployed 10-feature model?

Forward selection on data before 2026-06 only (2-year training), then one holdout score.
Usage: python3 research5.py minutes_2y.pkl
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research import logloss
from research2 import DEPLOY
from research3 import walk, report

warnings.filterwarnings('ignore')


def indicators(df):
    p = df['open']; tp = df['typ'].shift(1); v = df['vol'].shift(1)   # finished minutes only
    out = pd.DataFrame(index=df.index)
    for fast, slow, sig in [(12, 26, 9), (60, 130, 45)]:            # 1-min and ~5-min-equivalent MACD
        m = p.ewm(span=fast, adjust=False).mean() - p.ewm(span=slow, adjust=False).mean()
        out[f'macd_{fast}'] = m / p * 1e4
        out[f'macdh_{fast}'] = (m - m.ewm(span=sig, adjust=False).mean()) / p * 1e4
    for n in (20, 60):
        ma, sd = p.rolling(n).mean(), p.rolling(n).std()
        out[f'bb_{n}'] = (p - ma) / (2 * sd.replace(0, np.nan))      # Bollinger %B, centred
        out[f'cci_{n}'] = (tp - tp.rolling(n).mean()) / (0.015 * (tp - tp.rolling(n).mean()).abs().rolling(n).mean())
    for n in (60, 240):
        vwap = (tp * v).rolling(n).sum() / v.rolling(n).sum().replace(0, np.nan)
        out[f'vwap_{n}'] = (p / vwap - 1) * 1e4
    for n in (14, 60):
        hi, lo = p.rolling(n).max(), p.rolling(n).min()
        out[f'stoch_{n}'] = (p - lo) / (hi - lo).replace(0, np.nan)
        out[f'stochd_{n}'] = out[f'stoch_{n}'].rolling(3).mean()
    for n in (20, 60):
        e = p.ewm(span=n, adjust=False).mean()
        out[f'ema_slope_{n}'] = (e / e.shift(5) - 1) * 1e4
    # trend efficiency (ADX-like): net move / path length over 60 and 240 minutes
    for n in (60, 240):
        out[f'eff_{n}'] = (p - p.shift(n)).abs() / p.diff().abs().rolling(n).sum().replace(0, np.nan)
    return out


def main(path):
    df = load(path)
    f = build(df).join(indicators(df))
    win = windows(df, f)
    IND = [c for c in indicators(df.iloc[:5]).columns]
    sel = win[win.index < '2026-06-01']
    print('univariate (follow the indicator), before 2026-06:')
    for c in IND:
        s = np.sign(sel[c] - (0.5 if c.startswith('stoch') else 0)); hit = ((s > 0) == (sel['up'] == 1))[s != 0]
        print(f'  {c:14s} {hit.mean()*100:5.2f}%')

    def sel_gain(cols):   # selection-period-only score: walk-forward months Jan-May 2026, 2y training
        p = walk(win, cols, '2024-10-01'); m = p.notna() & (win.index < '2026-06-01')
        y = win['up'][m].values
        return (logloss(y, np.full(len(y), y.mean())) - logloss(y, p[m].values)) * 1e4, p

    base, p0 = sel_gain(DEPLOY)
    print('\nbaseline selection gain', round(base, 1))
    cur, best_p = list(DEPLOY), p0
    for rnd in range(3):
        cands = [(c, sel_gain(cur + [c])) for c in IND if c not in cur]
        c, (g, p) = max(cands, key=lambda x: x[1][0])
        print(f'round {rnd}: best add {c} -> {g:.1f} (+{g-base:.1f})')
        if g - base < 2: break
        cur.append(c); base, best_p = g, p
    print('\nchosen:', cur[len(DEPLOY):] or 'nothing')
    print(json.dumps(report('live 10 features', win, p0)))
    if cur != DEPLOY:
        print(json.dumps(report('10 + indicators', win, best_p)))


if __name__ == '__main__':
    main(sys.argv[1])
