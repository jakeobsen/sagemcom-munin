#!/usr/bin/env python3
"""Munin multigraph plugin for DOCSIS modem stats.

Reads the latest channel data from the modem_stats SQLite database
and exposes three graphs:
  - modem_downstream_power  (dBmV per channel)
  - modem_downstream_snr    (dB per channel)
  - modem_upstream_power    (dBmV per channel)

Installation (via Makefile):
  make install-munin

Manual installation:
  ln -s /path/to/munin.py /etc/munin/plugins/modem_

  In /etc/munin/plugin-conf.d/modem:
    [modem_*]
    env.db_path /path/to/modem_stats.db

Requires: munin 2.0+ (multigraph support)
"""

import os
import sqlite3
import sys

DB_PATH = os.environ.get("db_path", "/opt/modem-logger/modem_stats.db")


def get_latest_timestamp(conn):
    """Get the most recent timestamp from downstream_channels."""
    row = conn.execute(
        "SELECT timestamp FROM downstream_channels ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def get_channels(conn, table, timestamp):
    """Get all channel rows for a given timestamp."""
    return conn.execute(
        f"SELECT * FROM {table} WHERE timestamp = ? ORDER BY channel_id",
        (timestamp,),
    ).fetchall()


def config_downstream_power(channels):
    print("multigraph modem_downstream_power")
    print("graph_title DOCSIS Downstream Power")
    print("graph_vlabel dBmV")
    print("graph_category network")
    print("graph_info Downstream channel power levels. Ideal range is -7 to +7 dBmV.")
    for ch in channels:
        cid = ch["channel_id"]
        freq_mhz = ch["frequency_hz"] / 1_000_000 if ch["frequency_hz"] else "?"
        print(f"ds_ch{cid}_power.label Ch {cid} ({freq_mhz} MHz)")
        print(f"ds_ch{cid}_power.type GAUGE")
        print(f"ds_ch{cid}_power.warning -7:7")
        print(f"ds_ch{cid}_power.critical -10:10")


def config_downstream_snr(channels):
    print("multigraph modem_downstream_snr")
    print("graph_title DOCSIS Downstream SNR")
    print("graph_vlabel dB")
    print("graph_category network")
    print("graph_info Downstream channel signal-to-noise ratio. Should be above 33 dB.")
    for ch in channels:
        cid = ch["channel_id"]
        freq_mhz = ch["frequency_hz"] / 1_000_000 if ch["frequency_hz"] else "?"
        print(f"ds_ch{cid}_snr.label Ch {cid} ({freq_mhz} MHz)")
        print(f"ds_ch{cid}_snr.type GAUGE")
        print(f"ds_ch{cid}_snr.warning 33:")
        print(f"ds_ch{cid}_snr.critical 30:")


def config_upstream_power(channels):
    print("multigraph modem_upstream_power")
    print("graph_title DOCSIS Upstream Power")
    print("graph_vlabel dBmV")
    print("graph_category network")
    print("graph_info Upstream channel power levels. Ideal range is 35 to 49 dBmV.")
    for ch in channels:
        cid = ch["channel_id"]
        freq_mhz = ch["frequency_hz"] / 1_000_000 if ch["frequency_hz"] else "?"
        print(f"us_ch{cid}_power.label Ch {cid} ({freq_mhz} MHz)")
        print(f"us_ch{cid}_power.type GAUGE")
        print(f"us_ch{cid}_power.warning 35:49")
        print(f"us_ch{cid}_power.critical 30:54")


def fetch_downstream_power(channels):
    print("multigraph modem_downstream_power")
    for ch in channels:
        cid = ch["channel_id"]
        val = ch["power_dbmv"] if ch["power_dbmv"] is not None else "U"
        print(f"ds_ch{cid}_power.value {val}")


def fetch_downstream_snr(channels):
    print("multigraph modem_downstream_snr")
    for ch in channels:
        cid = ch["channel_id"]
        val = ch["snr_db"] if ch["snr_db"] is not None else "U"
        print(f"ds_ch{cid}_snr.value {val}")


def fetch_upstream_power(channels):
    print("multigraph modem_upstream_power")
    for ch in channels:
        cid = ch["channel_id"]
        val = ch["power_dbmv"] if ch["power_dbmv"] is not None else "U"
        print(f"us_ch{cid}_power.value {val}")


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    ts = get_latest_timestamp(conn)
    if ts is None:
        # No data yet — output empty config/values so munin doesn't error
        if len(sys.argv) > 1 and sys.argv[1] == "config":
            for graph in ["modem_downstream_power", "modem_downstream_snr", "modem_upstream_power"]:
                print(f"multigraph {graph}")
                print("graph_title No data yet")
                print("graph_category network")
        return

    ds_channels = [dict(r) for r in get_channels(conn, "downstream_channels", ts)]
    us_channels = [dict(r) for r in get_channels(conn, "upstream_channels", ts)]
    conn.close()

    if len(sys.argv) > 1 and sys.argv[1] == "config":
        config_downstream_power(ds_channels)
        print()
        config_downstream_snr(ds_channels)
        print()
        config_upstream_power(us_channels)
    else:
        fetch_downstream_power(ds_channels)
        print()
        fetch_downstream_snr(ds_channels)
        print()
        fetch_upstream_power(us_channels)


if __name__ == "__main__":
    main()
