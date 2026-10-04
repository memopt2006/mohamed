"""Walk-forward research for Robinhood BTC 15-minute up/down markets.

Usage: python3 research.py minutes.pkl
Every model is re-fit monthly on data before that month and scored on that month only.
"""
import sys, json, warnings
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import lightgbm as lgb
from features import load, build, windows, inwindow, W

warnings.filterwarnings('ignore')

FEATS = ['ret_1', 'ret_5', 'ret_15', 'ret_30', 'ret_60', 'ret_240', 'ret_1440',
         'rv_15', 'rv_60', 'rv_240', 'rv_1440', 'rv_ratio', 'rv_ratio2',
         'z_15', 'z_60', 'z_240', 'vz_15', 'vz_60',
         'rangepos_60', 'rangepos_240', 'rangepos_1440', 'sma_dev_60', 'sma_dev_240',
         'rsi_14', 'rsi15_14', 'gap_15', 'gap_chg', 'ret_last2',
         'hour', 'dow', 'weekend', 'prev_up', 'prev_move_z', 'streak']
SMALL = ['z_15', 'z_60', 'z_240', 'rsi_14', 'rangepos_60', 'gap_15', 'prev_move_z', 'rv_ratio', 'ret_1']


def logloss(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def walk_forward(win, fit_predict, min_train_months=3):
    months = win.index.to_period('M')
    um = sorted(months.unique())
    preds = pd.Series(np.nan, index=win.index)
    for m in um[min_train_months:]:
        tr, te = months < m, months == m
        preds[te] = fit_predict(win[tr], win[te])
    return preds


def m_const(tr, te):
    return np.full(len(te), tr['up'].mean())


def m_fade60(tr, te):
    return np.where(te['ret_60'] > 0, 0.45, 0.55)


def m_logit(cols, C=0.05):
    def f(tr, te):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))
        m.fit(tr[cols], tr['up'])
        return m.predict_proba(te[cols])[:, 1]
    return f


def m_lgb(cols):
    def f(tr, te):
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.02, num_leaves=15,
                               min_child_samples=400, subsample=0.8, subsample_freq=1,
                               colsample_bytree=0.7, reg_lambda=5.0, verbose=-1)
        m.fit(tr[cols], tr['up'])
        return m.predict_proba(te[cols])[:, 1]
    return f


def score(name, y, p, extra=None):
    ok = ~np.isnan(p)
    y, p = y[ok], p[ok]
    acc = float(np.mean((p >= 0.5) == (y == 1)))
    base = logloss(y, np.full(len(y), y.mean()))
    r = {'model': name, 'n': int(len(y)), 'acc': round(acc * 100, 2),
         'logloss_gain_bp': round((base - logloss(y, p)) * 1e4, 1),
         'brier': round(float(np.mean((p - y) ** 2)), 4)}
    # selective accuracy: only the most confident 10/25%
    conf = np.abs(p - 0.5)
    for q in (0.75, 0.9):
        sel = conf >= np.quantile(conf, q)
        r[f'acc_top{int(round((1 - q) * 100))}'] = round(float(np.mean((p[sel] >= 0.5) == (y[sel] == 1))) * 100, 2)
    if extra:
        r.update(extra)
    return r


def by_half(y, p):
    ok = ~np.isnan(p)
    y, p = y[ok], p[ok]
    h = len(y) // 2
    return [round(float(np.mean((p[:h] >= .5) == (y[:h] == 1))) * 100, 2),
            round(float(np.mean((p[h:] >= .5) == (y[h:] == 1))) * 100, 2)]


# ---------- in-window fair value ----------

def fair_prob(d, t, sigma1m, kappa=1.0):
    """P(settle >= target) given log-distance d at minute t of the window.

    Remaining variance until the 60-second settlement average: price diffuses for
    (W-1-t) more minutes, then the final minute is averaged (variance 1/3 of a minute).
    """
    rem = np.maximum((W - 1 - t) + 1 / 3, 1 / 3)
    return norm.cdf(d / (kappa * sigma1m * np.sqrt(rem)))


def main(path):
    df = load(path)
    f = build(df)
    win = windows(df, f)
    print(f'windows: {len(win)}  from {win.index.min()} to {win.index.max()}  up-rate {win.up.mean():.4f}')
    y = win['up'].values
    results = []
    models = {
        'always_base_rate': m_const,
        'fade_1h (current app rule)': m_fade60,
        'logit_small': m_logit(SMALL),
        'logit_all': m_logit(FEATS),
        'lightgbm_all': m_lgb(FEATS),
    }
    preds = {}
    for name, fn in models.items():
        p = walk_forward(win, fn).values
        preds[name] = p
        results.append(score(name, y, p, {'halves': by_half(y, p)}))
    ens = np.nanmean(np.vstack([preds['logit_all'], preds['lightgbm_all']]), axis=0)
    preds['ensemble'] = ens
    results.append(score('ensemble (logit+lgb)', y, ens, {'halves': by_half(y, ens)}))

    # univariate signal check: hit rate of fading / following each move, by month
    uni = {}
    for c in ['ret_1', 'ret_5', 'ret_15', 'ret_60', 'ret_240', 'gap_15', 'prev_move_z', 'rsi_14']:
        s = np.sign(win[c] - (50 if c == 'rsi_14' else 0))
        hit = ((s > 0) == (win['up'] == 1))[s != 0]
        uni[c] = round(float(hit.mean()) * 100, 2)
    # by hour (fade_1h hit rate)
    fade_hit = ((win['ret_60'] <= 0) == (win['up'] == 1))
    by_hour = fade_hit.groupby(win.index.hour).mean().round(4).to_dict()
    by_month = fade_hit.groupby(win.index.to_period('M').astype(str)).mean().round(4).to_dict()

    # ---------- in-window fair value calibration ----------
    iw = inwindow(df, f)
    iw = iw[iw['rv'] > 0]
    months = iw['ws'].dt.to_period('M')
    um = sorted(months.unique())
    cal_tr = iw[months < um[3]]
    best = None
    for kappa in np.arange(0.6, 1.61, 0.05):
        ll = logloss(cal_tr['up'].values, fair_prob(cal_tr['d'].values, cal_tr['t'].values, cal_tr['rv'].values, kappa))
        if best is None or ll < best[1]:
            best = (round(float(kappa), 2), ll)
    kappa = best[0]
    te = iw[months >= um[3]].copy()
    te['p'] = fair_prob(te['d'].values, te['t'].values, te['rv'].values, kappa)
    te['bin'] = (te['p'] * 10).clip(0, 9.999).astype(int)
    calib = te.groupby('bin').agg(pred=('p', 'mean'), actual=('up', 'mean'), n=('up', 'size')).round(4)
    calib_by_t = te.groupby('t').apply(lambda g: round(logloss(g['up'].values, g['p'].values), 4)).to_dict()

    out = {'n_windows': int(len(win)), 'models': results, 'univariate_follow_hit_pct': uni,
           'fade_by_hour_utc': by_hour, 'fade_by_month': by_month,
           'fair_value': {'kappa': kappa, 'calibration': calib.reset_index().to_dict('records'),
                          'logloss_by_minute': calib_by_t}}
    print(json.dumps(out, indent=1, default=str))
    pd.DataFrame(preds, index=win.index).assign(up=y).to_pickle(path.replace('.pkl', '_preds.pkl'))
    return out


if __name__ == '__main__':
    main(sys.argv[1])
