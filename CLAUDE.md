# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Dynatrace Extension Framework 2.0 (EF2) Python extension (`custom:file-monitor`). It runs under OneAgent, stats the configured files on each poll, and reports `custom.file.*` metrics split by a `file_path` dimension.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"               # dt-extensions-sdk (module: dynatrace_extension) + pyyaml for dev mode

# Run locally from the repo root (SDK reads extension/extension.yaml relative to cwd).
# Metrics are buffered and printed to stdout ~once a minute, so run for 60s+.
python -m file_monitor --activationconfig activation_config.json

# Package and deploy (dt CLI)
dt extension gencerts                 # first time only; writes certificates/ (gitignored, never commit)
dt extension build                    # produces signed custom_file-monitor-<version>.zip
dt extension upload custom_file-monitor-<version>.zip
```

The repo has no test suite and no linter config. To verify a change, run the extension locally against `activation_config.json` after pointing it at real files.

SDK gotchas for local runs:
- The flag is `--activationconfig` in lowercase. The SDK uses `parse_known_args`, so a misspelled flag (such as `--activationConfig` or a made-up `--fastDevelopmentMode`) is silently ignored, and the SDK falls back to a nonexistent `activation.json` and runs with an empty config.
- The activation config file must wrap the settings in `"pythonLocal": {...}`. `self.activation_config.get(...)` reads from inside that key.

## Architecture

The extension has three parts that must agree with each other:

- **`src/file_monitor/__main__.py`**: `FileMonitorExtension(Extension)` from `dynatrace_extension`. The SDK calls `query()` on every poll. It reads `self.activation_config["endpoints"]` and runs `_collect()` for each entry, which calls `self.report_metric(...)`. To report status from `query()`, return a `Status`. The SDK has no `report_status()` method.
- **`extension/extension.yaml`**: the manifest. It declares:
  - every metric key under `metrics:`
  - the `activationSchema`, which defines the shape of `endpoints` (`file_path`, `count_lines`)
  - the topology type, which creates one entity per `file_path` from any `custom.file*` metric and maps dimensions to entity attributes
  - the entity screens, which hold the properties card and charts
  - the bundled dashboard
  - the Python entrypoint, `file_monitor.__main__:main`
- **`dashboards/overview.json`**: the bundled dashboard, referenced from the manifest.

The config contract has two sides. `activation_config.json` is the local stand-in for what OneAgent passes at runtime, so it must match `activationSchema`.

### Cross-file rules when changing things

- **New metric:** declare it in `extension.yaml` `metrics:` and also report it in `_collect()`. Optionally add it to `screens` chartsCards and the dashboard.
- **New config parameter:** add it under `activationSchema.types.endpoint.properties`, read it with `endpoint.get(...)` in `query()`/`_collect()`, and update `activation_config.json`.
- **New dimension:** add it to the `dims` dict. To show it in the UI, also add a topology `attributes` entry and a `propertiesCard` property.
- **Version bumps:** update both `setup.py` and `extension.yaml` `version`, which are currently kept in sync at 1.1.0. The built zip name comes from the manifest version.

### Behavioral details

- **Missing file:** zeros are reported for `exists`/`size_bytes`/`age_seconds`/`change_age_seconds`, using only the `file_path` dimension. When the file exists, the full dimension set is used, adding `file_owner`, `file_group`, `file_mountpoint`, and `file_mode_octal`.
- **Platforms:** the code is cross-platform. `pwd`/`grp` are imported only off Windows, and on Windows owner and group are reported as `"N/A"`. `st_ctime` means metadata-change time on Unix and creation time on Windows.
- **`count_lines`:** reads the whole file on every poll, so it should stay opt-in.
- **`custom.file.owner_uid`:** reported only on Unix. On Windows `st_uid` is always 0, so the metric is skipped there.
