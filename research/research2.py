"""Stage 2: selective-trading economics, stability, in-window fair value model, deployable logit.

Usage: python3 research2.py minutes.pkl
"""
import sys, json, warnings
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from features import load, build, windows, inwindow, W
from research import walk_forward, m_logit, m_lgb, logloss, FEATS, SMALL, fair_prob

DEPLOY = SMALL + ['rangepos_240']   # chosen by select_feats.py on data before 2026-05-04 only

warnings.filterwarnings('ignore')


def econ(p, y, thresholds=(0.52, 0.53, 0.54, 0.55, 0.56, 0.57, 0.58), entries=(0.50, 0.52, 0.54)):
    """Trade the predicted side when model prob for that side >= thr; pay a fixed entry price."""
    rows = []
    side_p = np.where(p >= 0.5, p, 1 - p)
    win = np.where(p >= 0.5, y == 1, y == 0)
    for thr in thresholds:
        sel = side_p >= thr
        if sel.sum() == 0:
            continue
        hr = win[sel].mean()
        r = {'min_prob': thr, 'trades': int(sel.sum()), 'per_day': round(sel.sum() / (len(p) / 96), 1),
             'hit_pct': round(hr * 100, 2)}
        for e in entries:
            r[f'pnl_per_trade_at_{int(e*100)}c'] = round(hr - e, 4)
        rows.append(r)
    return rows


def monthly(p, y, idx, thr):
    side_p = np.where(p >= 0.5, p, 1 - p)
    win = np.where(p >= 0.5, y == 1, y == 0)
    sel = side_p >= thr
    d = pd.DataFrame({'m': idx.to_period('M').astype(str), 'sel': sel, 'win': win})
    g = d[d.sel].groupby('m')['win'].agg(['mean', 'size'])
    return {k: [round(v['mean'] * 100, 1), int(v['size'])] for k, v in g.iterrows()}


def main(path):
    df = load(path)
    f = build(df)
    win = windows(df, f)
    y = win['up'].values
    ok_months = win.index.to_period('M')

    p_small = walk_forward(win, m_logit(DEPLOY)).values
    p_all = walk_forward(win, m_logit(FEATS)).values
    p_lgb = walk_forward(win, m_lgb(FEATS)).values
    p_ens = np.nanmean(np.vstack([p_all, p_lgb, p_small]), axis=0)
    pre_src = p_small   # the live app uses the deployable model, so the in-window model is fit on it
    m = ~np.isnan(p_small)
    out = {'test_windows': int(m.sum()), 'test_from': str(win.index[m][0])}
    for name, p in [('logit10', p_small), ('ensemble3', p_ens)]:
        out[f'econ_{name}'] = econ(p[m], y[m])
        out[f'monthly_{name}_p55'] = monthly(p[m], y[m], win.index[m], 0.55)
        # strength bands as used live, on the untouched holdout (2026-06 onward) and before it
        sp = np.where(p >= .5, p, 1 - p); wn = np.where(p >= .5, y == 1, y == 0)
        for per, mask in [('selection', m & (win.index < '2026-06-01')), ('holdout', m & (win.index >= '2026-06-01'))]:
            bands = {}
            for lo, hi, nm in [(0.55, 1, 'strong'), (0.53, 0.55, 'medium'), (0, 0.53, 'weak')]:
                b = mask & (sp >= lo) & (sp < hi)
                bands[nm] = [round(float(wn[b].mean()) * 100, 2), int(b.sum())]
            out[f'bands_{name}_{per}'] = bands

    # ---- deployable model: logit_small fit on everything except the last month (for SQL) ----
    sc = StandardScaler().fit(win[DEPLOY])
    lr = LogisticRegression(C=0.05, max_iter=2000).fit(sc.transform(win[DEPLOY]), win['up'])
    out['deploy_logit_small'] = {'features': DEPLOY, 'mean': sc.mean_.round(10).tolist(),
                                 'scale': sc.scale_.round(10).tolist(),
                                 'coef': lr.coef_[0].round(6).tolist(), 'intercept': round(float(lr.intercept_[0]), 6)}

    # ---- in-window: random-walk vs fitted model that adds pre-window signal ----
    iw = inwindow(df, f)
    iw = iw[iw['rv'] > 0].copy()
    pre = pd.Series(pre_src, index=win.index)
    iw['p_pre'] = iw['ws'].map(pre)
    iw['rem'] = np.maximum((W - 1 - iw['t']) + 1 / 3, 1 / 3)
    iw['z'] = iw['d'] / (iw['rv'] * np.sqrt(iw['rem']))
    iw['rw'] = norm.cdf(iw['z'] / 0.95)
    iw = iw.dropna(subset=['p_pre'])
    iw['lpre'] = np.log(iw['p_pre'] / (1 - iw['p_pre']))
    iw['zt'] = iw['z'] * np.sqrt(iw['t'])
    mon = iw['ws'].dt.to_period('M')
    um = sorted(mon.unique())
    cols = ['z', 'lpre', 'zt']
    preds = pd.Series(np.nan, index=iw.index)
    for mm in um[1:]:
        tr, te = mon < mm, mon == mm
        lr2 = LogisticRegression(C=1.0, max_iter=2000).fit(iw.loc[tr, cols], iw.loc[tr, 'up'])
        preds[te] = lr2.predict_proba(iw.loc[te, cols])[:, 1]
    iw['fit'] = preds
    ev = iw.dropna(subset=['fit'])
    out['inwindow_logloss'] = {'random_walk': round(logloss(ev['up'].values, ev['rw'].values), 5),
                               'fitted_with_signal': round(logloss(ev['up'].values, ev['fit'].values), 5),
                               'n': int(len(ev))}
    lr_final = LogisticRegression(C=1.0, max_iter=2000).fit(iw[cols], iw['up'])
    out['deploy_inwindow'] = {'cols': cols, 'coef': lr_final.coef_[0].round(6).tolist(),
                              'intercept': round(float(lr_final.intercept_[0]), 6)}
    # How often does the fitted fair value disagree with a naive 'random walk' price by >= 5c?
    out['inwindow_gap_ge5c_share'] = round(float((np.abs(ev['fit'] - ev['rw']) >= 0.05).mean()), 4)
    # value of trading the fitted edge vs. a market that prices like the random walk (+2c spread)
    edge = ev['fit'] - ev['rw']
    for thr in (0.03, 0.05, 0.08):
        buy_yes = edge >= thr + 0.02
        buy_no = edge <= -(thr + 0.02)
        pnl = np.concatenate([(ev['up'][buy_yes] - (ev['rw'][buy_yes] + 0.02)).values,
                              ((1 - ev['up'][buy_no]) - (1 - ev['rw'][buy_no] + 0.02)).values])
        out[f'vs_rw_market_edge{int(thr*100)}c'] = {'trades': int(len(pnl)), 'avg_pnl': round(float(pnl.mean()), 4) if len(pnl) else None}
    print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
