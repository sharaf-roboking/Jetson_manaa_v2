#!/usr/bin/env python3
"""
Dual u-blox logger (F9R + M91) with:

Always:
  - RAW logs (.bin) per receiver
  - UBX-style logs (.ubx) using pyubx2 UBXReader
  - Timestamped text logs (_text.log)
  - NMEA-only logs (_nmea.txt)

Optional (controlled by flags below):
  - NAV-PVT CSV logs in per-receiver 'csv' folder
  - ESF-INS CSV logs in per-receiver 'csv' folder

Folder structure (example):

gnss_logs/
  F9R/
    raw/
      YYYYMMDD_HHMMSS_F9R.bin
      YYYYMMDD_HHMMSS_F9R_text.log
      YYYYMMDD_HHMMSS_F9R_nmea.txt
    ubx/
      YYYYMMDD_HHMMSS_F9R.ubx
    csv/               (only if CSV flags enabled)
      YYYYMMDD_HHMMSS_F9R_navpvt.csv
      YYYYMMDD_HHMMSS_F9R_esfins.csv
  M91/
    raw/
      YYYYMMDD_HHMMSS_M91.bin
      YYYYMMDD_HHMMSS_M91_text.log
      YYYYMMDD_HHMMSS_M91_nmea.txt
    ubx/
      YYYYMMDD_HHMMSS_M91.ubx
    csv/
      YYYYMMDD_HHMMSS_M91_navpvt.csv
      YYYYMMDD_HHMMSS_M91_esfins.csv   (likely empty if ESF-INS not output)

Requires:
  - pyubx2: pip install pyubx2
  - udev symlinks:
      /dev/gnss_f9r
      /dev/gnss_m91
"""

import os
import sys
import time
import threading
import serial
from datetime import datetime, timezone
from pyubx2 import UBXReader, NMEA_PROTOCOL, UBX_PROTOCOL
import subprocess
import ctypes
import numpy as np
    
# ===== USER SETTINGS =====

PORTS = {
    #"F9R": "/dev/gnss_f9r",
    #"M91": "/dev/gnss_m91",
    "F9R":"/dev/ttyUSB2",
}
BAUDRATE = 38400
BASE_LOG_DIR = "./ublox/gnss_logs"

# Enable/disable CSV logging
ENABLE_NAVPVT_CSV = True   # set True to log UBX-NAV-PVT into CSV
ENABLE_ESFINS_CSV = True   # set True to log UBX-ESF-INS into CSV

# =========================

running = True  # global flag for clean shutdown


def utc_timestamp_for_filename() -> str:
    """Return UTC timestamp suitable for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def utc_iso() -> str:
    """Return ISO 8601 UTC timestamp for text logs."""
    return datetime.now(timezone.utc).isoformat()


def is_nmea_sentence(s: str) -> bool:
    """
    Very simple NMEA detector:
    - strip leading whitespace
    - check if it starts with $G or $P (GNSS or proprietary)
    """
    s = s.lstrip()
    if not s.startswith("$"):
        return False
    return s.startswith("$G") or s.startswith("$P")


def navpvt_csv_header() -> str:
    """Header line for NAV-PVT CSV."""
    cols = [
        "time_utc",     # from UBX fields (year, month, day, hour, min, sec)
        "iTOW_ms",
        "lat_deg",
        "lon_deg",
        "height_m",
        "hMSL_m",
        "hAcc_m",
        "vAcc_m",
        "gSpeed_mps",
        "headMot_deg",
        "fixType",
        "numSV",
    ]
    return ",".join(cols)


def navpvt_to_csv_row(parsed) -> str:
    """
    Convert a UBX-NAV-PVT message to a CSV row.
    pyubx2 UBXMessage typically provides:
      lon, lat in 1e-7 deg
      height, hMSL, hAcc, vAcc in mm
      gSpeed in mm/s
      headMot in 1e-5 deg
    """
    # Build UTC time string from UBX fields, if available
    try:
        year = parsed.year
        month = parsed.month
        day = parsed.day
        hour = parsed.hour
        minute = parsed.min
        second = parsed.second
        time_utc = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
    except Exception:
        time_utc = ""

    def safe_get(attr, default=""):
        return getattr(parsed, attr, default)

    iTOW = safe_get("iTOW", "")
    lon = safe_get("lon", "")
    lat = safe_get("lat", "")
    height = safe_get("height", "")
    hMSL = safe_get("hMSL", "")
    hAcc = safe_get("hAcc", "")
    vAcc = safe_get("vAcc", "")
    gSpeed = safe_get("gSpeed", "")
    headMot = safe_get("headMot", "")
    fixType = safe_get("fixType", "")
    numSV = safe_get("numSV", "")

    # Convert fixed-point units if needed
    try:
        lon_deg = float(lon) * 1e-7 if lon not in ("", None) else ""
    except Exception:
        lon_deg = ""
    try:
        lat_deg = float(lat) * 1e-7 if lat not in ("", None) else ""
    except Exception:
        lat_deg = ""
    try:
        height_m = float(height) / 1000.0 if height not in ("", None) else ""
    except Exception:
        height_m = ""
    try:
        hMSL_m = float(hMSL) / 1000.0 if hMSL not in ("", None) else ""
    except Exception:
        hMSL_m = ""
    try:
        hAcc_m = float(hAcc) / 1000.0 if hAcc not in ("", None) else ""
    except Exception:
        hAcc_m = ""
    try:
        vAcc_m = float(vAcc) / 1000.0 if vAcc not in ("", None) else ""
    except Exception:
        vAcc_m = ""
    try:
        gSpeed_mps = float(gSpeed) / 1000.0 if gSpeed not in ("", None) else ""
    except Exception:
        gSpeed_mps = ""
    try:
        headMot_deg = float(headMot) * 1e-5 if headMot not in ("", None) else ""
    except Exception:
        headMot_deg = ""

    fields = [
        time_utc,
        str(iTOW),
        "" if lon_deg == "" else f"{lon_deg:.9f}",
        "" if lat_deg == "" else f"{lat_deg:.9f}",
        "" if height_m == "" else f"{height_m:.3f}",
        "" if hMSL_m == "" else f"{hMSL_m:.3f}",
        "" if hAcc_m == "" else f"{hAcc_m:.3f}",
        "" if vAcc_m == "" else f"{vAcc_m:.3f}",
        "" if gSpeed_mps == "" else f"{gSpeed_mps:.3f}",
        "" if headMot_deg == "" else f"{headMot_deg:.5f}",
        str(fixType),
        str(numSV),
    ]
    return ",".join(fields)


def esfins_header_and_row(parsed, existing_header=None):
    """
    Build a header and row for ESF-INS messages.
    We introspect the parsed message's attributes and keep the useful ones.
    Returns (header_list, row_list). If existing_header is given, we reuse it.
    """
    attrs = {
        k: v for k, v in parsed.__dict__.items()
        if not k.startswith("_")
    }

    # Remove generic UBXMessage internals if present
    for k in ("identity", "name", "msg_cls", "msg_id", "payload", "length", "checksum"):
        attrs.pop(k, None)

    if existing_header is None:
        header = list(attrs.keys())
    else:
        header = existing_header

    # Ensure all header fields are present in attrs, missing → ""
    row = [str(attrs.get(col, "")) for col in header]
    return header, row


def log_from_receiver(name: str, port: str):
    """
    Per-receiver logging thread:
      - open serial port
      - use UBXReader to read messages (UBX + NMEA)
      - write raw stream to .bin
      - write message-by-message stream to .ubx
      - write decoded text + NMEA-only logs
      - optionally write UBX-NAV-PVT & ESF-INS messages to CSV
    """
    global running

    # Create receiver-specific directories
    timestr = time.strftime("%Y%m%d-%H%M%S");
    output_file_path = f"./results/ublox{timestr}/"
    rec_dir = output_file_path; # os.path.join(BASE_LOG_DIR, name)
    raw_dir = os.path.join(rec_dir, "raw")
    ubx_dir = os.path.join(rec_dir, "ubx")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(ubx_dir, exist_ok=True)

    # CSV directory only if any CSV logging is enabled
    csv_dir = None
    if ENABLE_NAVPVT_CSV or ENABLE_ESFINS_CSV:
        csv_dir = os.path.join(rec_dir, "csv")
        os.makedirs(csv_dir, exist_ok=True)

    ts = utc_timestamp_for_filename()
    base_raw = os.path.join(raw_dir, f"{ts}_{name}")
    base_ubx = os.path.join(ubx_dir, f"{ts}_{name}")

    fname_bin = base_raw + ".bin"
    fname_txt = base_raw + "_text.log"
    fname_nmea = base_raw + "_nmea.txt"
    fname_ubx = base_ubx + ".ubx"

    # CSV filenames (only used if flags enabled)
    fname_csv_navpvt = None
    fname_csv_esfins = None
    if csv_dir is not None:
        if ENABLE_NAVPVT_CSV:
            fname_csv_navpvt = os.path.join(csv_dir, f"{ts}_{name}_navpvt.csv")
        if ENABLE_ESFINS_CSV:
            fname_csv_esfins = os.path.join(csv_dir, f"{ts}_{name}_esfins.csv")

    print(f"[{name}] Opening {port} @ {BAUDRATE} baud")
    try:
        stream = serial.Serial(port, BAUDRATE, timeout=3)
    except serial.SerialException as e:
        print(f"[{name}] ERROR opening port {port}: {e}")
        return

    print(f"[{name}] Logging to:")
    print(f"    RAW   -> {fname_bin}")
    print(f"    UBX   -> {fname_ubx}")
    print(f"    TEXT  -> {fname_txt}")
    print(f"    NMEA  -> {fname_nmea}")
    if ENABLE_NAVPVT_CSV and fname_csv_navpvt:
        print(f"    NAVPVT CSV -> {fname_csv_navpvt}")
    if ENABLE_ESFINS_CSV and fname_csv_esfins:
        print(f"    ESF-INS CSV -> {fname_csv_esfins}")

    f_bin = open(fname_bin, "wb")
    f_ubx = open(fname_ubx, "wb")
    f_txt = open(fname_txt, "w", buffering=1)
    f_nmea = open(fname_nmea, "w", buffering=1)

    f_csv_navpvt = None
    f_csv_esfins = None
    esfins_header = None

    if ENABLE_NAVPVT_CSV and fname_csv_navpvt:
        f_csv_navpvt = open(fname_csv_navpvt, "w", buffering=1)
        f_csv_navpvt.write(navpvt_csv_header() + "\n")

    if ENABLE_ESFINS_CSV and fname_csv_esfins:
        f_csv_esfins = open(fname_csv_esfins, "w", buffering=1)
        # header for ESF-INS will be written when first ESF-INS message arrives

    # UBXReader handles message framing for UBX + NMEA
    ubr = UBXReader(
        stream,
        protfilter=NMEA_PROTOCOL | UBX_PROTOCOL,
        bufsize=4096,
    )

    try:
        while running:
            try:
                raw_data, parsed = ubr.read()
            except Exception as e:
                print(f"[{name}] UBXReader error: {e}")
                break

            if not raw_data:
                # timeout or no data
                continue

            # 1) Write raw bytes as continuous stream
            f_bin.write(raw_data)

            # 2) Write UBX-style log (message-by-message)
            f_ubx.write(raw_data)

            # 3) Decode to text for logs
            try:
                text = raw_data.decode(errors="replace").rstrip("\r\n")
            except Exception:
                text = ""

            if text:
                t_iso = utc_iso()
                f_txt.write(f"{t_iso} [{name}] {text}\n")

                # 4) NMEA-only log
                if is_nmea_sentence(text):
                    lib = ctypes.CDLL("./lib_cc_access.so");
                    lib.read_cpu_cycle_counter.restype = ctypes.c_uint64;
                    end = ctypes.c_uint64(lib.read_cpu_cycle_counter());
                    write_time = datetime.now();
                    formatted_write_time = write_time.strftime("%Y-%m-%d %H:%M:%S");
                    f_nmea.write("data" + " captured on " + formatted_write_time + " and at CPU cycle:" + f"{end}" + "\n");
                    f_nmea.write(text + "\n")

            # 5) NAV-PVT CSV log (optional)
            if (
                ENABLE_NAVPVT_CSV
                and f_csv_navpvt is not None
                and parsed
                and getattr(parsed, "identity", "") == "NAV-PVT"
            ):
                try:
                    row = navpvt_to_csv_row(parsed)
                    f_csv_navpvt.write(row + "\n")
                except Exception as e:
                    print(f"[{name}] NAV-PVT CSV error: {e}")

            # 6) ESF-INS CSV log (optional, typically F9R only)
            if (
                ENABLE_ESFINS_CSV
                and f_csv_esfins is not None
                and parsed
                and getattr(parsed, "identity", "") == "ESF-INS"
            ):
                try:
                    header, row_vals = esfins_header_and_row(parsed, existing_header=esfins_header)
                    if esfins_header is None:
                        esfins_header = header
                        f_csv_esfins.write(",".join(esfins_header) + "\n")
                    f_csv_esfins.write(",".join(row_vals) + "\n")
                except Exception as e:
                    print(f"[{name}] ESF-INS CSV error: {e}")

    except Exception as e:
        print(f"[{name}] Unexpected error in logging loop: {e}")

    # Cleanup
    try:
        stream.close()
    except Exception:
        pass

    for f in (f_bin, f_ubx, f_txt, f_nmea, f_csv_navpvt, f_csv_esfins):
        if f is None:
            continue
        try:
            f.close()
        except Exception:
            pass

    print(f"[{name}] Stopped logging and closed files/port.")


def main():
    global running

    threads = []
    for name, port in PORTS.items():
        t = threading.Thread(
            target=log_from_receiver,
            args=(name, port),
            daemon=True,
        )
        t.start()
        threads.append(t)

    # initiate cpu cycle access if not already
    #result = subprocess.run(["sudo", "rmmod", "pmu_el0_cycle_counter"], capture_output=True, text=True);
    #result = subprocess.run(["sudo", "insmod", "./pmu_el0_cycle_counter.ko"], capture_output=True, text=True);
    #print(f"Return code: {result.returncode}");
    #print(f"Output: {result.stdout}");
    #if result.stderr:
    #    print(f"Errors: {result.stderr}");
    #lib = ctypes.CDLL("./lib_cc_access.so");
    #lib.read_cpu_cycle_counter.restype = ctypes.c_uint64;
    #start = ctypes.c_uint64(lib.read_cpu_cycle_counter());
    #cc_file = open("./angle_time.txt","w");

    print("\n=== Dual u-blox logger (raw + ubx + text + nmea + optional CSV) ===")
    print("Recording from:")
    for name, port in PORTS.items():
        print(f"  - {name} on {port}")
    print(f"\nNAV-PVT CSV logging: {'ON' if ENABLE_NAVPVT_CSV else 'OFF'}")
    print(f"ESF-INS CSV logging: {'ON' if ENABLE_ESFINS_CSV else 'OFF'}")
    print("\nPress Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(0.2)  # avoid busy-waiting
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping logging...")
        running = False

        for t in threads:
            t.join()

        print("[MAIN] All receivers stopped. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()

