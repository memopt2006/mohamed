"""Decode research.export_flow() dumps into a per-minute DataFrame (v, tbv in BTC)."""
import re, sys
import numpy as np, pandas as pd

def main(out, files):
    frames = {}
    for path in files:
        s = open(path).read()
        for m in re.finditer(r'"x\\?":\\?"(\d{4}-\d{2}-\d{2})\|([^"\\]*)', s):
            day, body = m.group(1), m.group(2)
            recs = body.split(';')
            v = np.array([float(r.split(',')[0]) / 1e4 if r.split(',')[0] else np.nan for r in recs])
            t = np.array([float(r.split(',')[1]) / 1e4 if r.split(',')[1] else np.nan for r in recs])
            frames[day] = pd.DataFrame({'v': v, 'tbv': t}, index=pd.date_range(day, periods=len(recs), freq='min', tz='UTC'))
    df = pd.concat([frames[d] for d in sorted(frames)])
    df.to_pickle(out)
    print(len(frames), 'days', len(df), 'minutes; missing', round(df.v.isna().mean(), 4), '; avg BTC/min', round(df.v.mean(), 4))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
