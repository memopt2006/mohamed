"""Fit the deployed model on all available data and refit the in-window fair value model.

Usage: python3 fit_final.py minutes.pkl walkforward_preds.pkl out_model.json
walkforward_preds.pkl: column '2y training' with out-of-sample pre-window probabilities.
"""
import sys, json, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from features import load, build, windows, inwindow, W
from research2 import DEPLOY

warnings.filterwarnings('ignore')
df = load(sys.argv[1]); f = build(df); win = windows(df, f)
sc = StandardScaler().fit(win[DEPLOY])
lr = LogisticRegression(C=0.05, max_iter=2000).fit(sc.transform(win[DEPLOY]), win['up'])
out = {'deploy_logit_small': {'features': DEPLOY, 'mean': sc.mean_.round(10).tolist(), 'scale': sc.scale_.round(10).tolist(),
                              'coef': lr.coef_[0].round(6).tolist(), 'intercept': round(float(lr.intercept_[0]), 6),
                              'trained_on': [str(win.index.min()), str(win.index.max())], 'n_windows': int(len(win))}}
# in-window model: same form as research2, fit on out-of-sample pre-window probabilities
pre = pd.read_pickle(sys.argv[2])['2y training']
iw = inwindow(df, f); iw = iw[iw['rv'] > 0].copy()
iw['p_pre'] = iw['ws'].map(pre); iw = iw.dropna(subset=['p_pre'])
iw['rem'] = np.maximum((W - 1 - iw['t']) + 1 / 3, 1 / 3)
iw['z'] = iw['d'] / (iw['rv'] * np.sqrt(iw['rem']))
iw['lpre'] = np.log(iw['p_pre'] / (1 - iw['p_pre'])); iw['zt'] = iw['z'] * np.sqrt(iw['t'])
lr2 = LogisticRegression(C=1.0, max_iter=2000).fit(iw[['z', 'lpre', 'zt']], iw['up'])
out['deploy_inwindow'] = {'cols': ['z', 'lpre', 'zt'], 'coef': lr2.coef_[0].round(6).tolist(),
                          'intercept': round(float(lr2.intercept_[0]), 6), 'n': int(len(iw))}
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print(json.dumps(out)[:900])
