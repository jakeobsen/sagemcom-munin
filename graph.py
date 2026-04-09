#!/usr/bin/env python3
"""Generate signal quality graphs from logged modem stats."""

import sqlite3
import sys
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

import config


def query(conn: sqlite3.Connection, sql: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql).fetchall()]


def plot_downstream(conn: sqlite3.Connection):
    """Plot downstream power and SNR over time."""
    rows = query(
        conn,
        """
        SELECT timestamp, channel_id, power_dbmv, snr_db
        FROM downstream_channels
        ORDER BY timestamp, channel_id
        """,
    )
    if not rows:
        print("No downstream data to plot.")
        return

    # Group by channel
    channels: dict[int, dict] = {}
    for r in rows:
        cid = r["channel_id"]
        if cid not in channels:
            channels[cid] = {"times": [], "power": [], "snr": []}
        channels[cid]["times"].append(datetime.fromisoformat(r["timestamp"]))
        channels[cid]["power"].append(r["power_dbmv"])
        channels[cid]["snr"].append(r["snr_db"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle("Downstream Channels", fontsize=14)

    for cid in sorted(channels):
        ch = channels[cid]
        ax1.plot(ch["times"], ch["power"], label=f"Ch {cid}", alpha=0.7, linewidth=0.8)
        ax2.plot(ch["times"], ch["snr"], label=f"Ch {cid}", alpha=0.7, linewidth=0.8)

    ax1.set_ylabel("Power (dBmV)")
    ax1.axhspan(-7, 7, color="green", alpha=0.08, label="Ideal range")
    ax1.legend(fontsize=6, ncol=6, loc="upper right")
    ax1.grid(True, alpha=0.3)

    ax2.set_ylabel("SNR (dB)")
    ax2.axhline(y=33, color="orange", linestyle="--", alpha=0.5, label="Min recommended")
    ax2.legend(fontsize=6, ncol=6, loc="upper right")
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig("downstream.png", dpi=150)
    print("Saved downstream.png")


def plot_upstream(conn: sqlite3.Connection):
    """Plot upstream power over time."""
    rows = query(
        conn,
        """
        SELECT timestamp, channel_id, power_dbmv
        FROM upstream_channels
        ORDER BY timestamp, channel_id
        """,
    )
    if not rows:
        print("No upstream data to plot.")
        return

    channels: dict[int, dict] = {}
    for r in rows:
        cid = r["channel_id"]
        if cid not in channels:
            channels[cid] = {"times": [], "power": []}
        channels[cid]["times"].append(datetime.fromisoformat(r["timestamp"]))
        channels[cid]["power"].append(r["power_dbmv"])

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.suptitle("Upstream Channels", fontsize=14)

    for cid in sorted(channels):
        ch = channels[cid]
        ax.plot(ch["times"], ch["power"], label=f"Ch {cid}", alpha=0.7, linewidth=0.8)

    ax.set_ylabel("Power (dBmV)")
    ax.axhspan(35, 49, color="green", alpha=0.08, label="Ideal range")
    ax.legend(fontsize=6, ncol=4, loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig("upstream.png", dpi=150)
    print("Saved upstream.png")


def main():
    conn = sqlite3.connect(config.DB_PATH)
    plot_downstream(conn)
    plot_upstream(conn)
    conn.close()


if __name__ == "__main__":
    main()
