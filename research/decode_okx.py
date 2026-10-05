"""Decode research.export_okx() dumps into a per-minute DataFrame: basis ($), pv (BTC), eth (USD)."""
import re, sys
import numpy as np, pandas as pd

def main(out, files):
    frames = {}
    for path in files:
        s = open(path).read()
        for m in re.finditer(r'"x\\?":\\?"(\d{4}-\d{2}-\d{2})\|([^"\\]*)', s):
            day, recs = m.group(1), m.group(2).split(';')
            n = len(recs); basis = np.full(n, np.nan); pv = np.full(n, np.nan); eth = np.full(n, np.nan)
            last = None
            for k, r in enumerate(recs):
                a, b, c = r.split(',')
                if a: basis[k] = int(a)
                if b: pv[k] = int(b) / 10
                if c == '': last = None
                else:
                    last = int(c[1:]) if c.startswith('=') else last + int(c)
                    eth[k] = last / 100
            frames[day] = pd.DataFrame({'basis': basis, 'pv': pv, 'eth': eth},
                                       index=pd.date_range(day, periods=n, freq='min', tz='UTC'))
    df = pd.concat([frames[d] for d in sorted(frames)])
    df.to_pickle(out)
    print(len(frames), 'days', len(df), 'minutes; missing basis', round(df.basis.isna().mean(), 4),
          'eth', round(df.eth.isna().mean(), 4), '; median basis $', df.basis.median())

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
