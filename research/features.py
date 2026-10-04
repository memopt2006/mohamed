"""Build 15-minute window dataset from per-minute proxy prices.

Settlement mimics Robinhood/CF Benchmarks: target K = index at window start,
settle S = average of the index over the final 60 seconds (typical price of
the last 1-minute bar). Index proxy = average of Coinbase and Bitstamp.
"""
import numpy as np, pandas as pd

W = 15  # window length, minutes


def load(path):
    df = pd.read_pickle(path)
    full = pd.date_range(df.index.min(), df.index.max(), freq='min', tz='UTC')
    df = df.reindex(full)
    df['open'] = df['open'].ffill()
    df['typ'] = df['typ'].fillna(df['open'])
    df['vol'] = df['vol'].fillna(0)
    df['gap'] = df['gap'].fillna(0)
    return df


def rsi(x, n):
    d = x.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def build(df):
    p = df['open']                      # price at the start of each minute
    lp = np.log(p)
    r1 = lp.diff()
    f = pd.DataFrame(index=df.index)
    for k in (1, 5, 15, 30, 60, 240, 1440):
        f[f'ret_{k}'] = lp - lp.shift(k)
    for k in (15, 60, 240, 1440):
        f[f'rv_{k}'] = r1.rolling(k).std()
    f['rv_ratio'] = f['rv_15'] / f['rv_240']
    f['rv_ratio2'] = f['rv_60'] / f['rv_1440']
    # trend-normalised moves (z-scores)
    for k in (15, 60, 240):
        f[f'z_{k}'] = f[f'ret_{k}'] / (f['rv_240'] * np.sqrt(k))
    v = df['vol'].shift(1)          # minute T's volume isn't known at T
    f['vz_15'] = np.log1p(v.rolling(15).sum()) - np.log1p(v.rolling(1440).sum() / 96)
    f['vz_60'] = np.log1p(v.rolling(60).sum()) - np.log1p(v.rolling(1440).sum() / 24)
    for k in (60, 240, 1440):
        hi, lo = p.rolling(k).max(), p.rolling(k).min()
        f[f'rangepos_{k}'] = (p - lo) / (hi - lo).replace(0, np.nan)
    f['sma_dev_60'] = lp - np.log(p.rolling(60).mean())
    f['sma_dev_240'] = lp - np.log(p.rolling(240).mean())
    f['rsi_14'] = rsi(p, 14)
    f['rsi15_14'] = rsi(p.where(df.index.minute % 15 == 0).dropna(), 14).reindex(df.index).ffill()
    # Coinbase-Bitstamp premium (USD), smoothed
    g = df['gap'].shift(1)          # close-to-close gap of the finished minute
    f['gap_15'] = g.rolling(15).mean() / p * 1e4
    f['gap_chg'] = (g.rolling(5).mean() - g.rolling(60).mean()) / p * 1e4
    # last-minute micro moves
    f['ret_last2'] = lp - lp.shift(2)
    f['hour'] = df.index.hour
    f['dow'] = df.index.dayofweek
    f['weekend'] = (f['dow'] >= 5).astype(int)
    return f


def windows(df, f):
    idx = df.index[(df.index.minute % W == 0)]
    idx = idx[(idx + pd.Timedelta(minutes=W - 1)) <= df.index[-1]]
    K = df['open'].reindex(idx).values
    S = df['typ'].reindex(idx + pd.Timedelta(minutes=W - 1)).values
    out = f.reindex(idx).copy()
    out['K'] = K
    out['S'] = S
    out['up'] = (S >= K).astype(int)
    out['move'] = S - K
    # previous window outcomes (known at window start)
    out['prev_up'] = out['up'].shift(1)
    out['prev_move_z'] = (out['move'].shift(1) / K) / (out['rv_240'] * np.sqrt(W))
    out['streak'] = out['prev_up'].groupby((out['prev_up'] != out['prev_up'].shift()).cumsum()).cumcount() + 1
    out['streak'] = out['streak'] * np.where(out['prev_up'] == 1, 1, -1)
    return out.dropna()


def inwindow(df, f, step=1):
    """Rows for every minute t (0..14) inside each window: state -> did it settle up?"""
    idx = df.index[(df.index.minute % W == 0)]
    idx = idx[(idx + pd.Timedelta(minutes=W - 1)) <= df.index[-1]]
    K = df['open'].reindex(idx).values
    S = df['typ'].reindex(idx + pd.Timedelta(minutes=W - 1)).values
    rv = f['rv_60'].reindex(idx).values
    rows = []
    for t in range(1, W, step):
        P = df['open'].reindex(idx + pd.Timedelta(minutes=t)).values
        rows.append(pd.DataFrame({'ws': idx, 't': t, 'K': K, 'P': P, 'S': S, 'rv': rv}))
    r = pd.concat(rows, ignore_index=True).dropna()
    r['up'] = (r['S'] >= r['K']).astype(int)
    r['d'] = np.log(r['P'] / r['K'])
    return r
