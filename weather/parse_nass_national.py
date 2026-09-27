"""
B3 — parse the USDA NASS national 'Crop Progress' text reports (spring 2025)
into a tidy weekly table for the 12 study states.

Source files (public, primary source):
    https://release.nass.usda.gov/reports/prog{WW}25.txt     WW = 14 … 27
    (released every Monday; each report describes the week ending the Sunday before)

Extracted per state and week (current-week column only):
    days_suitable                     Days Suitable for Fieldwork
    topsoil_vs / _s / _a / _su        Topsoil Moisture Condition (% very short, short, adequate, surplus)
    corn_planted, corn_planted_avg    Corn Planted (% ; 2020-2024 average)

Usage:
    python weather/parse_nass_national.py <dir_with_prog*.txt> <out_csv>
"""
import sys, os, re, glob, csv, datetime

STATES = ['Illinois', 'Indiana', 'Iowa', 'Kansas', 'Michigan', 'Minnesota', 'Missouri',
          'Nebraska', 'North Dakota', 'Ohio', 'South Dakota', 'Wisconsin']

MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July',
                                      'August', 'September', 'October', 'November', 'December'], 1)}


def num(tok):
    tok = tok.strip()
    if tok in ('-', '(NA)', '(D)', '(X)', '(Z)'):
        return 0.0 if tok == '-' else None
    try:
        return float(tok)
    except ValueError:
        return None


def section(lines, title_regex):
    """Return the lines of the first table whose title matches title_regex
    (from the title line to the closing dashed rule after the data rows)."""
    for i, ln in enumerate(lines):
        if re.match(title_regex, ln.strip(), flags=re.I):
            out, rules = [], 0
            for j in range(i, min(i + 120, len(lines))):
                out.append(lines[j])
                if re.match(r'^-{20,}\s*$', lines[j].strip()):
                    rules += 1
                    if rules >= 4:          # title rule, header rule(s), closing rule
                        break
            return out
    return None


def rows(table):
    """yield (state, [numbers...]) for 'State ....:  a  b  c' rows."""
    for ln in table or []:
        m = re.match(r'^\s*([A-Za-z][A-Za-z .]*?)\s*\.{2,}\s*:\s*(.+?)\s*$', ln)
        if not m:
            m = re.match(r'^\s*([A-Za-z][A-Za-z ]*?)\s*:\s+([-\d(].*?)\s*$', ln)
        if not m:
            continue
        name = m.group(1).strip()
        vals = [num(t) for t in m.group(2).split()]
        yield name, vals


def week_ending(lines):
    """Read 'Week Ending <Month> <d>, <yyyy>' from the topsoil table title."""
    txt = ' '.join(l.strip() for l in lines)
    m = re.search(r'Topsoil Moisture Condition - Selected States: Week Ending\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})', txt)
    if m:
        return datetime.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    return None


def main(src_dir, out_csv):
    recs = []
    for f in sorted(glob.glob(os.path.join(src_dir, 'prog*25.txt'))):
        with open(f, encoding='latin-1') as fh:
            lines = fh.read().splitlines()
        we = week_ending(lines)
        if we is None:
            print('  skip (no week-ending found):', os.path.basename(f)); continue
        ds = dict(rows(section(lines, r'^Days Suitable for Fieldwork - Selected States')))
        ts = dict(rows(section(lines, r'^Topsoil Moisture Condition - Selected States')))
        cp = dict(rows(section(lines, r'^Corn Planted - Selected States')))
        for st in STATES:
            d = ds.get(st); t = ts.get(st); c = cp.get(st)
            recs.append(dict(
                week_ending=we.isoformat(), state=st, source=os.path.basename(f),
                days_suitable=(d[-1] if d else None),
                topsoil_vs=(t[0] if t and len(t) >= 4 else None),
                topsoil_s=(t[1] if t and len(t) >= 4 else None),
                topsoil_a=(t[2] if t and len(t) >= 4 else None),
                topsoil_su=(t[3] if t and len(t) >= 4 else None),
                corn_planted=(c[2] if c and len(c) >= 4 else None),
                corn_planted_avg=(c[3] if c and len(c) >= 4 else None),
            ))
        print(f'  {os.path.basename(f)}  week ending {we}  '
              f'NE days={ds.get("Nebraska", [None])[-1]}  OH days={ds.get("Ohio", [None])[-1]}')
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0].keys()))
        w.writeheader(); w.writerows(recs)
    print(f'wrote {out_csv}  ({len(recs)} rows)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
