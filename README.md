# Dynatrace OneAgent Extension 2.0 — File Monitor

A customizable example showing how to build a **Dynatrace Extension Framework 2.0 (EF2)** extension that monitors files on a host and reports custom metrics into Dynatrace.

## What it does

For each configured file path the extension reports these metrics every polling cycle:

| Metric key | Description |
|---|---|
| `custom.file.exists` | `1` if the file exists, `0` if not |
| `custom.file.size_bytes` | File size in bytes |
| `custom.file.age_seconds` | Seconds since the file was last modified |
| `custom.file.line_count` | Line count (only when `count_lines: true`) |
| `custom.file.change_age_seconds` | Seconds since the file's metadata last changed (ctime; creation time on Windows) |
| `custom.file.mode` | Numeric permission bits (e.g. `420` = `0o644`) |
| `custom.file.owner_uid` | Numeric user ID of the file owner (Unix only) |

Metrics are split by the `file_path` dimension (existing files also carry `file_owner`, `file_group`, `file_mountpoint` and `file_mode_octal`) so you can monitor multiple files from a single extension activation. A built-in topology type (`custom:file-monitor`) creates entities per file, and a dashboard is bundled with the extension.

---

## Prerequisites

| Tool | Purpose |
|---|---|
| Python 3.8+ | Run and develop the extension |
| [Dynatrace CLI (`dt`)](https://docs.dynatrace.com/docs/extend-dynatrace/extensions20/dt-cli) | Build, sign, and upload the extension |
| OneAgent 1.239+ | Deployed on the host(s) you want to monitor |
| Dynatrace tenant | Where the extension is uploaded and activated |

Install the Python SDK and development tools:

```bash
pip install dt-extensions-sdk pyyaml
```

---

## Project layout

```
cffileextension/
├── extension/
│   └── extension.yaml       # Extension manifest — metrics, topology, UI screens
├── src/
│   └── file_monitor/
│       ├── __init__.py
│       └── __main__.py      # Extension logic — edit this to customise behaviour
├── dashboards/
│   └── overview.json        # Bundled dashboard uploaded with the extension
├── activation_config.json   # Example config for local testing
├── setup.py
└── README.md
```

---

## Local development & testing

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Run the extension locally

```bash
python -m file_monitor --activationconfig activation_config.json
```

Run it from the repo root: in local mode the SDK reads `extension/extension.yaml` relative to the working directory. Metrics are buffered and printed to stdout about once a minute, so let it run for at least 60 s before expecting output. In production they are sent to the OneAgent.

Edit `activation_config.json` to point at real files on your machine:

```json
{
  "enabled": true,
  "pythonLocal": {
    "endpoints": [
      { "file_path": "C:\\Windows\\System32\\drivers\\etc\\hosts", "count_lines": true },
      { "file_path": "C:\\Temp\\my-export.csv", "count_lines": false }
    ]
  }
}
```

---

## Customising the extension

### Add a new metric

1. Declare it in `extension/extension.yaml` under `metrics:`:

```yaml
metrics:
  - key: custom.file.word_count
    metadata:
      displayName: File Word Count
      unit: Count
      description: Number of whitespace-separated tokens
```

2. Report it in `src/file_monitor/__main__.py` inside `_collect()`:

```python
with open(file_path, "r", errors="ignore") as f:
    words = sum(len(line.split()) for line in f)
self.report_metric("custom.file.word_count", words, dimensions=dims)
```

### Add a configuration parameter

Add the parameter to `activationSchema` in `extension.yaml`:

```yaml
activationSchema:
  types:
    endpoint:
      properties:
        encoding:
          displayName: File Encoding
          description: Text encoding to use when reading the file
          type: text
          nullable: false
          default: "utf-8"
```

Then read it in `__main__.py`:

```python
encoding = endpoint.get("encoding", "utf-8")
with open(file_path, "r", encoding=encoding, errors="ignore") as f:
    ...
```

---

## Build and upload

### 1. Generate certificates (first time only)

```bash
dt extension gencerts
```

This creates a `certificates/` directory with a developer certificate and CA certificate. Upload the CA certificate to your Dynatrace tenant under **Settings > Web and mobile monitoring > Extension certificates**.

> **Do not commit `certificates/` to source control.** It is in `.gitignore`.

### 2. Build the extension

```bash
dt extension build
```

This produces a signed `.zip` file (e.g. `custom_file-monitor-1.0.0.zip`) in the project root.

### 3. Upload to Dynatrace

```bash
dt extension upload custom_file-monitor-1.0.0.zip
```

Or upload manually via **Dynatrace > Hub > Manage extensions > Upload custom extension**.

### 4. Activate on a host

1. In Dynatrace go to **Hub > Manage extensions** and find *File Monitor*.
2. Click **Add monitoring configuration**.
3. Select the host(s) running OneAgent.
4. Add one row per file under the **Files** section.
5. Enable **Count Lines** for text files where you need the line count metric.
6. Save — OneAgent picks up the config within ~30 seconds.

---

## Alerting example

Once metrics are flowing, create an anomaly detection rule:

- **Metric:** `custom.file.age_seconds`
- **Condition:** value > `3600` (file not updated in 1 hour)
- **Splitting:** by `file_path`

This fires a problem card if any monitored file goes stale.

---

## Resources

- [Extension Framework 2.0 overview](https://docs.dynatrace.com/docs/extend-dynatrace/extensions20)
- [Python Extension SDK reference](https://developer.dynatrace.com/develop/extensions/python-extension-sdk/)
- [extension.yaml reference](https://docs.dynatrace.com/docs/extend-dynatrace/extensions20/extension-yaml)
- [dt CLI reference](https://docs.dynatrace.com/docs/extend-dynatrace/extensions20/dt-cli)
