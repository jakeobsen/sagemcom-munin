#!/usr/bin/env python3
"""Fetch DOCSIS channel stats from a Sagemcom modem and log to SQLite."""

import asyncio
import json
import logging
import sys

from sagemcom_api.client import SagemcomClient
from sagemcom_api.enums import EncryptionMethod
from sagemcom_api.exceptions import (
    AuthenticationException,
    LoginTimeoutException,
)

import config
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

DOWNSTREAM_XPATH = "Device/Docsis/CableModem/Downstreams"
UPSTREAM_XPATH = "Device/Docsis/CableModem/Upstreams"


def parse_downstream_channels(data: list[dict]) -> list[dict]:
    """Extract relevant fields from downstream channel data."""
    channels = []
    for ch in data:
        channels.append(
            {
                "channel_id": ch.get("uid") or ch.get("channel_id"),
                "frequency_hz": ch.get("frequency"),
                "power_dbmv": ch.get("power_level"),
                "snr_db": ch.get("SNR"),
                "modulation": ch.get("modulation"),
                "locked": 1 if ch.get("lock_status") or ch.get("locked") else 0,
                "channel_type": ch.get("channel_type"),
            }
        )
    return channels


def parse_upstream_channels(data: list[dict]) -> list[dict]:
    """Extract relevant fields from upstream channel data."""
    channels = []
    for ch in data:
        channels.append(
            {
                "channel_id": ch.get("uid") or ch.get("channel_id"),
                "frequency_hz": ch.get("frequency"),
                "power_dbmv": ch.get("power_level"),
                "modulation": ch.get("modulation"),
                "locked": 1 if ch.get("lock_status") or ch.get("locked") else 0,
                "channel_type": ch.get("channel_type"),
            }
        )
    return channels


async def fetch_and_log():
    """Authenticate, fetch DOCSIS stats, store in SQLite."""
    client = SagemcomClient(
        host=config.MODEM_HOST,
        username=config.MODEM_USERNAME,
        password=config.MODEM_PASSWORD,
        authentication_method=EncryptionMethod.SHA512,
    )

    try:
        log.info("Logging in to %s...", config.MODEM_HOST)
        await client.login()
        log.info("Login successful")

        log.info("Fetching DOCSIS channel stats...")
        data = await client.get_values_by_xpaths(
            {
                "upstream": UPSTREAM_XPATH,
                "downstream": DOWNSTREAM_XPATH,
            },
            options={"capability-flags": {"interface": True}},
        )

        if "--debug" in sys.argv:
            print(json.dumps(data, indent=2, default=str))

        timestamp = db.now_iso()
        conn = db.connect(config.DB_PATH)

        downstream_raw = data.get("downstream", [])
        upstream_raw = data.get("upstream", [])

        if not isinstance(downstream_raw, list):
            downstream_raw = [downstream_raw] if downstream_raw else []
        if not isinstance(upstream_raw, list):
            upstream_raw = [upstream_raw] if upstream_raw else []

        downstream = parse_downstream_channels(downstream_raw)
        upstream = parse_upstream_channels(upstream_raw)

        db.insert_downstream(conn, timestamp, downstream)
        db.insert_upstream(conn, timestamp, upstream)
        conn.close()

        log.info(
            "Logged %d downstream and %d upstream channels at %s",
            len(downstream),
            len(upstream),
            timestamp,
        )

    except AuthenticationException:
        log.error("Authentication failed — check username/password in config.py")
        sys.exit(1)
    except LoginTimeoutException:
        log.error("Login timed out — is the modem reachable at %s?", config.MODEM_HOST)
        sys.exit(1)
    except Exception:
        log.exception("Unexpected error")
        sys.exit(1)
    finally:
        try:
            await client.logout()
        except Exception:
            pass
        await client.close()


def main():
    asyncio.run(fetch_and_log())


if __name__ == "__main__":
    main()
