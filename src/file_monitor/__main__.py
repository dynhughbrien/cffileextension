import os
import sys
import time
import stat as stat_module
from pathlib import Path

from dynatrace_extension import Extension, Status, StatusValue

# pwd/grp are Unix-only
if sys.platform != "win32":
    import pwd
    import grp


def _get_owner(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except Exception:
        return str(uid)


def _get_group(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except Exception:
        return str(gid)


def _get_mountpoint(path: Path) -> str:
    p = path.resolve()
    while not os.path.ismount(str(p)):
        p = p.parent
    return str(p)


class FileMonitorExtension(Extension):
    """
    OneAgent Extension 2.0 — monitors files on the host and reports
    size, age, mode, change time, and (optionally) line count as metrics.
    Owner, group, and mount point are reported as dimensions.

    Activation config shape (defined in extension.yaml activationSchema):
      endpoints:
        - file_path: /var/log/myapp.log
          count_lines: true
        - file_path: /data/export/output.csv
          count_lines: false
    """

    def initialize(self):
        self.logger.info("FileMonitorExtension starting up")

    def query(self):
        endpoints = self.activation_config.get("endpoints", [])

        if not endpoints:
            return Status(StatusValue.WARNING, "No file endpoints configured")

        for endpoint in endpoints:
            file_path = endpoint.get("file_path", "").strip()
            if not file_path:
                continue

            self._collect(file_path, count_lines=endpoint.get("count_lines", False))

    def _collect(self, file_path: str, count_lines: bool):
        base_dims = {"file_path": file_path}
        path = Path(file_path)

        if not path.exists():
            self.report_metric("custom.file.exists", 0, dimensions=base_dims)
            self.report_metric("custom.file.size_bytes", 0, dimensions=base_dims)
            self.report_metric("custom.file.age_seconds", 0, dimensions=base_dims)
            self.report_metric("custom.file.change_age_seconds", 0, dimensions=base_dims)
            self.logger.warning(f"File not found: {file_path}")
            return

        st = path.stat()
        now = time.time()

        # Build enriched dimensions that include string metadata
        if sys.platform != "win32":
            owner = _get_owner(st.st_uid)
            group = _get_group(st.st_gid)
        else:
            # Windows: st_uid/st_gid are always 0; use N/A
            owner = "N/A"
            group = "N/A"

        mode_octal = oct(stat_module.S_IMODE(st.st_mode))   # e.g. '0o644'
        mountpoint = _get_mountpoint(path)

        dims = {
            **base_dims,
            "file_owner": owner,
            "file_group": group,
            "file_mountpoint": mountpoint,
            "file_mode_octal": mode_octal,
        }

        # --- numeric metrics ---
        self.report_metric("custom.file.exists", 1, dimensions=dims)
        self.report_metric("custom.file.size_bytes", st.st_size, dimensions=dims)

        # mtime: last data modification
        self.report_metric("custom.file.age_seconds", now - st.st_mtime, dimensions=dims)

        # ctime: last metadata change (permissions, owner, link count) on Unix;
        #        creation time on Windows
        self.report_metric("custom.file.change_age_seconds", now - st.st_ctime, dimensions=dims)

        # File mode as raw integer — useful for detecting unexpected permission changes
        self.report_metric("custom.file.mode", stat_module.S_IMODE(st.st_mode), dimensions=dims)

        # Owner UID as raw integer — alert on ownership drift; name is in the file_owner dimension.
        # Skipped on Windows where st_uid is always 0.
        if sys.platform != "win32":
            self.report_metric("custom.file.owner_uid", st.st_uid, dimensions=dims)

        if count_lines:
            try:
                with open(file_path, "r", errors="ignore") as f:
                    lines = sum(1 for _ in f)
                self.report_metric("custom.file.line_count", lines, dimensions=dims)
            except OSError as exc:
                self.logger.error(f"Cannot read {file_path}: {exc}")

    def status(self):
        return Status(StatusValue.OK)


def main():
    FileMonitorExtension().run()


if __name__ == "__main__":
    main()
