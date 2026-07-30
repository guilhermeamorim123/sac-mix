"""
Publishes a new catalog data package (offFiles.zip) to the fleet panel's
database, so every DragX Mobile phone's daily auto-update check (see
docs/superpowers/specs/2026-07-30-dragx-mobile-catalog-autoupdate-design.md)
picks it up.

This script does NOT upload the zip itself -- commit it into
hardware-re/fleet-panel's static/ folder first (same convention already
used for DragX-NovoPacote.apk / DragX-Remover-Antigo.apk) and push, then
run this against the production database to point at its URL.

Run against the production database:
    DATABASE_URL=<production db url> python publish_catalog.py \
        <version> <url>

Example:
    DATABASE_URL=postgresql://... python publish_catalog.py \
        2 https://dragx-fleet-panel.onrender.com/static/offFiles-v2.zip
"""
import os
import sys

from db import get_engine, get_session_factory
from models import set_latest_catalog


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python publish_catalog.py <version> <url>")
    version = int(sys.argv[1])
    url = sys.argv[2]

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        print(f"Publishing to DATABASE_URL={database_url}")
    else:
        print("AVISO: DATABASE_URL não definida -- publicando no banco sqlite local (fleet_panel.db), não na produção!")

    engine = get_engine()
    session = get_session_factory(engine)()
    try:
        catalog = set_latest_catalog(session, version=version, url=url)
        print(f"Published catalog: version={catalog.version}")
        print(f"  url={catalog.url}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
