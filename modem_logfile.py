#!/usr/bin/env python3
"""Fetch the vendor log file from a Sagemcom modem and store in SQLite."""

import asyncio
import json
import logging
import sys
import urllib.parse

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


async def fetch_vendor_log(client: SagemcomClient) -> str | None:
    """Fetch the modem's vendor log file.

    Two-step process:
    1. Call getVendorLogDownloadURI to get a temporary download path
    2. GET that path to download the actual log content
    """
    action = {
        "id": 0,
        "method": "getVendorLogDownloadURI",
        "xpath": "Device/DeviceInfo/VendorLogFiles/VendorLogFile[@uid='1']",
        "parameters": {"FileName": "logFile"},
    }

    response = await client._SagemcomClient__api_request_async([action], False)
    uri = response["reply"]["actions"][0]["callbacks"][0]["parameters"]["uri"]
    log.info("Got log download URI: %s", uri)

    # Build the session cookie for the download GET request
    cookie_obj = {
        "req_id": client._request_id,
        "sess_id": client._session_id,
        "basic": False,
        "user": client.username,
        "dataModel": {
            "name": "Internal",
            "nss": [{"name": "gtw", "uri": "http://sagemcom.com/gateway-data"}],
        },
        "ha1": client._SagemcomClient__get_credential_hash(),
        "nonce": client._server_nonce,
    }
    cookie_str = json.dumps(cookie_obj, separators=(",", ":"))

    download_url = f"http://{config.MODEM_HOST}{uri}"
    headers = {"Cookie": f"session={urllib.parse.quote(cookie_str)}"}
    async with client.session.get(download_url, headers=headers) as resp:
        if resp.status == 200:
            return await resp.text()
        log.warning("Log download returned status %d", resp.status)
        return None


async def fetch_and_store_log():
    """Authenticate, fetch vendor log, store in SQLite."""
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

        log.info("Fetching modem vendor log...")
        log_text = await fetch_vendor_log(client)

        if "--debug" in sys.argv:
            print(log_text or "(empty)")

        if log_text:
            fetched_at = db.now_iso()
            conn = db.connect(config.DB_PATH)
            new_lines = db.insert_log_lines(conn, fetched_at, log_text)
            conn.close()
            if new_lines:
                log.info("Inserted %d new log line(s) at %s", new_lines, fetched_at)
            else:
                log.info("No new log lines")
        else:
            log.warning("No log content received")

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
    asyncio.run(fetch_and_store_log())


if __name__ == "__main__":
    main()
