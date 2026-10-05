"""Stage 4: let the model learn that snap-backs are stronger after big 4-hour moves and in the
2 PM-2 AM New York block (interaction terms), instead of filtering afterwards.

Usage: python3 research4.py minutes.pkl [train_from]
"""
import sys, json, warnings
import numpy as np, pandas as pd
from features import load, build, windows
from research2 import DEPLOY
from research3 import walk, report

warnings.filterwarnings('ignore')


def add_inter(win):
    a = np.abs(win['z_240'])
    ev = (~win.index.hour.isin(range(6, 18))).astype(float)
    win['abs_z240'] = a
    win['evening'] = ev
    for c in ('z_15', 'rangepos_240', 'prev_move_z', 'rangepos_60', 'rsi_14'):
        cc = win[c] - (0.5 if c.startswith('rangepos') else 50 if c == 'rsi_14' else 0)
        win[f'{c}_x_big'] = cc * a
        win[f'{c}_x_ev'] = cc * ev
    return win


def main(path, train_from):
    df = load(path)
    win = add_inter(windows(df, build(df)))
    INT_BIG = [f'{c}_x_big' for c in ('z_15', 'rangepos_240', 'prev_move_z', 'rangepos_60', 'rsi_14')]
    INT_EV = [f'{c}_x_ev' for c in ('z_15', 'rangepos_240', 'prev_move_z', 'rangepos_60', 'rsi_14')]
    for name, cols in [('10 features (live)', DEPLOY),
                       ('+ big-move interactions', DEPLOY + ['abs_z240'] + INT_BIG),
                       ('+ evening interactions', DEPLOY + ['evening'] + INT_EV),
                       ('+ both', DEPLOY + ['abs_z240', 'evening'] + INT_BIG + INT_EV)]:
        p = walk(win, cols, train_from)
        print(json.dumps(report(name, win, p)))
        ok = p.notna(); side = np.maximum(p, 1 - p)[ok]; y = win['up'][ok]
        right = np.where(p[ok] >= .5, y == 1, y == 0); hold = win.index[ok] >= '2026-06-01'
        for thr in (0.56, 0.57, 0.58):
            s = side.values >= thr
            print(f'   p>={thr}: sel {right[s & ~hold].mean()*100:.1f}% ({(s & ~hold).sum()})  hold {right[s & hold].mean()*100:.1f}% ({(s & hold).sum()})')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '2025-10-01')
