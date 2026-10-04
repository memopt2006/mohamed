"""Decode research.export_compact() dumps (saved MCP results) into a per-minute parquet/CSV.

Each day line: "YYYY-MM-DD|m0;m1;...;m1439", minute = "dOpen,typ-open,cb-bs,vol10".
dOpen is "=<abs>" after a gap, "" when the minute is missing.
"""
import json, re, sys, glob
import numpy as np, pandas as pd

def days_from_file(path):
    s = open(path).read()
    i, j = s.find('['), s.rfind(']')
    # the payload is JSON text inside the result envelope; rows look like {"x":"YYYY-MM-DD|..."}
    for m in re.finditer(r'"x\\?":\\?"(\d{4}-\d{2}-\d{2})\|([^"\\]*)', s):
        yield m.group(1), m.group(2)

def decode_day(day, body):
    mins = body.split(';')
    n = len(mins)
    po = np.full(n, np.nan); pt = np.full(n, np.nan); gap = np.full(n, np.nan); vol = np.full(n, np.nan)
    last = None
    for k, rec in enumerate(mins):
        a, b, c, d = rec.split(',')
        if a == '':
            last = None
        else:
            last = int(a[1:]) if a.startswith('=') else last + int(a)
            po[k] = last
            if b != '': pt[k] = last + int(b)
        if c != '': gap[k] = int(c)
        if d != '': vol[k] = int(d) / 10
    ts = pd.date_range(day, periods=n, freq='min', tz='UTC')
    return pd.DataFrame({'open': po, 'typ': pt, 'gap': gap, 'vol': vol}, index=ts)

if __name__ == '__main__':
    out = sys.argv[1]
    frames = {}
    for f in sys.argv[2:]:
        for day, body in days_from_file(f):
            frames[day] = decode_day(day, body)
    df = pd.concat([frames[d] for d in sorted(frames)])
    df = df[~df.index.duplicated(keep='last')]
    df.to_pickle(out)
    print(len(frames), 'days', len(df), 'minutes', df.open.isna().mean().round(4), 'missing frac', df.index.min(), df.index.max())
