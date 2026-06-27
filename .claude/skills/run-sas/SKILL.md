---
name: run-sas
description: Run SAS programs via connect_saspy, parse HTML output into DataFrames, and work with results. Use when asked to run, execute, or submit SAS code, or read/analyze SAS output.
---

# Running SAS Programs with connect_saspy

*Patterns for submitting SAS code and reading results using connect_saspy, pandas, and BeautifulSoup.*

---

## Step 1 — Ensure Required Packages Are Installed

Before any SAS work, verify and install all dependencies in a single idempotent block.

```python
import subprocess, sys

def _pip_install(*packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *packages])

try:
    import saspy
except ImportError:
    _pip_install("saspy")
    import saspy

try:
    import connect_saspy
except ImportError:
    _pip_install("git+https://github.com/matise-joe-norc/connect-saspy.git")
    import connect_saspy

try:
    import pandas as pd
except ImportError:
    _pip_install("pandas")
    import pandas as pd

try:
    import numpy as np
except ImportError:
    _pip_install("numpy")
    import numpy as np

try:
    from bs4 import BeautifulSoup
except ImportError:
    _pip_install("beautifulsoup4", "lxml")
    from bs4 import BeautifulSoup
```

**Required packages summary:**

| Package | Source | Purpose |
|---|---|---|
| `saspy` | PyPI | SAS session backend used by connect_saspy |
| `connect_saspy` | GitHub (matise-joe-norc) | Simplified SAS connection wrapper |
| `pandas` | PyPI | Parse HTML tables from LST output; data wrangling |
| `numpy` | PyPI | Numerical operations on results |
| `beautifulsoup4` | PyPI | Fine-grained HTML parsing of LST output |
| `lxml` | PyPI | Fast HTML parser backend required by `pandas.read_html` |

---

## Step 2 — Submit SAS Code

`connect_saspy` auto-starts a SAS session on first import and exposes a module-level `submit()`.  
The session uses `results="html"` — all LST output is HTML.

### Module-level convenience (recommended for simple use)

```python
import connect_saspy

lst = connect_saspy.submit("""
    proc print data=sashelp.class (obs=5);
    run;
""")
# lst is an HTML string, or None if SAS produced no printed output
print(lst)
```

### Class-level (recommended when managing multiple connections or lifecycle)

```python
from connect_saspy import SASConnection

sas = SASConnection()

lst = sas.submit("""
    data work.example;
        set sashelp.cars (obs=10);
    run;

    proc means data=work.example;
        var MSRP Invoice;
    run;
""")

sas.close()
```

**What `submit()` returns:**
- The SAS **LST** (list/output) as an **HTML string**, or `None` if no output was produced.
- The SAS **LOG** is always printed to stdout automatically — watch it for `ERROR:` and `WARNING:` lines.

---

## Step 3 — Parse Output into DataFrames

Because the LST is HTML, use `pandas.read_html()` to extract tables in one line.

```python
import pandas as pd
from io import StringIO

def sas_lst_to_dataframes(lst: str | None) -> list[pd.DataFrame]:
    """Return all HTML tables in the LST as a list of DataFrames."""
    if not lst:
        return []
    return pd.read_html(StringIO(lst))

# Example
lst = connect_saspy.submit("proc print data=sashelp.class; run;")
dfs = sas_lst_to_dataframes(lst)

for i, df in enumerate(dfs):
    print(f"--- Table {i} ---")
    print(df.head())
```

### Fine-grained parsing with BeautifulSoup

Use BeautifulSoup when you need to inspect titles, footnotes, or non-table content.

```python
from bs4 import BeautifulSoup

def parse_sas_output(lst: str | None) -> dict:
    """Extract titles, tables, and footnotes from SAS HTML output."""
    if not lst:
        return {"titles": [], "tables": [], "footnotes": []}

    soup = BeautifulSoup(lst, "lxml")
    return {
        "titles":     [t.get_text(strip=True) for t in soup.find_all(class_="c")],
        "tables":     pd.read_html(StringIO(lst)) if soup.find("table") else [],
        "footnotes":  [f.get_text(strip=True) for f in soup.find_all(class_="f")],
    }

result = parse_sas_output(lst)
print(result["titles"])
df = result["tables"][0]  # first table as DataFrame
```

---

## Step 4 — Check for Errors in the LOG

The LOG is printed to stdout by `submit()`, but you can also inspect it programmatically
via the underlying `saspy` session when you need to detect errors in code.

```python
from connect_saspy import get_connection

def submit_and_check(code: str) -> tuple[str | None, bool]:
    """Submit SAS code; return (lst, had_errors)."""
    sas_conn = get_connection()
    # Access the raw saspy session for log inspection
    session = sas_conn._sas_session
    if session is None:
        sas_conn._start_connection()
        session = sas_conn._sas_session

    result = session.submit(code)
    log  = result.get("LOG", "")
    lst  = result.get("LST")

    had_errors = any(
        line.lstrip().startswith(("ERROR:", "WARNING:"))
        for line in log.splitlines()
    )

    print("=== SAS LOG ===")
    print(log)
    print("=== END LOG ===")

    return lst, had_errors

lst, had_errors = submit_and_check("proc print data=sashelp.class; run;")
if had_errors:
    print("SAS reported errors or warnings — review the log above.")
```

---

## Common Patterns

### Read a SAS dataset into a pandas DataFrame

```python
lst = connect_saspy.submit("""
    proc print data=sashelp.cars noobs;
    run;
""")
df = sas_lst_to_dataframes(lst)[0]
```

### Run PROC MEANS and capture statistics

```python
lst = connect_saspy.submit("""
    proc means data=sashelp.cars n mean std min max;
        var MSRP Invoice;
    run;
""")
stats_df = sas_lst_to_dataframes(lst)[0]
print(stats_df)
```

### Pass Python data to SAS via a data step

```python
import pandas as pd

# Build a SAS data step from a Python dict
rows = [("North", 1000), ("South", 1500), ("East", 1200), ("West", 800)]
datalines = "\n".join(f"{region} {sales}" for region, sales in rows)

code = f"""
data work.sales;
    input region $ sales;
    datalines;
{datalines}
    ;
run;

proc means data=work.sales;
    var sales;
run;
"""

lst = connect_saspy.submit(code)
dfs = sas_lst_to_dataframes(lst)
```

### Close the connection explicitly

```python
# Module-level global connection
connect_saspy.close_connection()

# Class-instance connection
sas = connect_saspy.SASConnection()
# ... work ...
sas.close()
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `SASConfigNotFoundError` | `sascfg_personal.py` missing or misconfigured | See [SASPy configuration docs](https://sassoftware.github.io/saspy/install.html) |
| `lst` is `None` | SAS code ran but produced no printed output | Normal for `DATA` steps; use `PROC PRINT` to see data |
| `ERROR:` in LOG | SAS syntax error or missing dataset | Read the LOG carefully; correct the SAS code |
| `pd.read_html` raises `ValueError` | LST has no `<table>` elements | Use BeautifulSoup to inspect raw HTML first |
| Import fails for `connect_saspy` | Package not installed from GitHub | Run `pip install git+https://github.com/matise-joe-norc/connect-saspy.git` |

---

## saspy Configuration Prerequisite

`connect_saspy` delegates all SAS connectivity to `saspy`, which requires a
`sascfg_personal.py` configuration file. Common access methods:

```python
# Local SAS installation (IOM)
# sascfg_personal.py example:
SAS_config_names = ['winlocal']
winlocal = {
    'saspath': '/path/to/sas',
}

# SAS Viya / SAS Studio compute
# See: https://sassoftware.github.io/saspy/install.html
```

When `saspy` is not yet configured, run `import saspy; saspy.SAScfg` to find where the
config file should be placed, then follow the [SASPy install guide](https://sassoftware.github.io/saspy/install.html).
