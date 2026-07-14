"""
Publishes a new DragX release to the fleet panel's database, so every
machine's automatic update check (see
docs/superpowers/specs/2026-07-07-dragx-auto-update-design.md) picks it up
on its next cold start.

Computes the file's MD5 locally rather than requiring it as a separate
argument -- the vendor's own (unmodified) ForcedUpdateDialog download-
verification code checks this MD5 against the downloaded file, so it must
be correct or every machine's update install will fail its own integrity
check.

Run against the production database:
    DATABASE_URL=<production db url> python publish_release.py \
        <version_code> <version_name> <download_url> <local_apk_path>

Example:
    DATABASE_URL=postgresql://... python publish_release.py \
        706 V7.0.3.006 https://example.com/DragX-706-signed.apk ./DragX-706-signed.apk
"""
import hashlib
import sys

from db import get_engine, get_session_factory
from models import set_latest_release


def compute_md5(path):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
    return md5.hexdigest()


def main():
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: python publish_release.py <version_code> <version_name> <download_url> <local_apk_path>"
        )
    version_code = int(sys.argv[1])
    version_name = sys.argv[2]
    download_url = sys.argv[3]
    local_apk_path = sys.argv[4]

    file_md5 = compute_md5(local_apk_path)

    engine = get_engine()
    session = get_session_factory(engine)()
    try:
        release = set_latest_release(
            session,
            version_code=version_code,
            version_name=version_name,
            download_url=download_url,
            file_md5=file_md5,
        )
        print(f"Published release: version_code={release.version_code} version_name={release.version_name}")
        print(f"  download_url={release.download_url}")
        print(f"  file_md5={release.file_md5}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
