#!/usr/bin/env python3
"""
MANNA Celestial Navigation Camera Capture Script

Captures star images with exposure midpoint timestamps for
celestial-navigation calculations.

IMPORTANT:
Use Midpoint_UTC rather than T0 or T2 in the navigation algorithm.

Midpoint_UTC = T0_Trigger_UTC + (EXPOSURE_SECONDS / 2)
"""

import time
import datetime
import subprocess
import os
from pathlib import Path
import ctypes

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Exposure time in seconds.
# Must match the actual shutter speed used by the Sony camera.
EXPOSURE_SECONDS = 1.0/13.0

# Inclinometer data order.
# Your receive-angles.py writes values such as: -9,12 captured on ...
# This script assumes the first value is PITCH and the second value is ROLL.
# If your sensor sends roll,pitch instead, change this to "roll_pitch".
INCLINOMETER_VALUE_ORDER = "pitch_roll"

# ==============================================================================
# PROJECT PATHS
# ==============================================================================

# Absolute directory containing this Python script:
# ~/Downloads/camera/
SCRIPT_DIR = Path(__file__).resolve().parent

# Project root:
# ~/Downloads/
PROJECT_DIR = SCRIPT_DIR.parent

# Output location:
# ~/Downloads/results/
RESULTS_DIR = PROJECT_DIR / "results"

# PMU files
PMU_MODULE = SCRIPT_DIR / "pmu_el0_cycle_counter.ko"
CC_LIBRARY = SCRIPT_DIR / "lib_cc_access.so"

# ==============================================================================
# GPHOTO2 / LIBGPHOTO2 PATHS
# ==============================================================================

# IMPORTANT:
# Do not use Path.home() here if you intend to accidentally run this script
# through sudo, because sudo changes HOME to /root.
#
# This explicitly uses your normal Jetson user installation.

USER_HOME = Path("/home/manaa")

GPHOTO2_BIN = USER_HOME / ".local/bin/gphoto2"

LOCAL_LIB = USER_HOME / ".local/lib"

CAMLIBS = LOCAL_LIB / "libgphoto2/2.5.34.1"
IOLIBS = LOCAL_LIB / "libgphoto2_port/0.12.2"

# ==============================================================================
# GPHOTO2 ENVIRONMENT
# ==============================================================================

gphoto_env = os.environ.copy()

existing_ld_path = gphoto_env.get("LD_LIBRARY_PATH", "")

library_paths = [
    str(LOCAL_LIB),
    str(LOCAL_LIB / "aarch64-linux-gnu"),
]

if existing_ld_path:
    library_paths.append(existing_ld_path)

gphoto_env["LD_LIBRARY_PATH"] = ":".join(library_paths)
gphoto_env["CAMLIBS"] = str(CAMLIBS)
gphoto_env["IOLIBS"] = str(IOLIBS)

# ==============================================================================
# VERIFY GPHOTO2 INSTALLATION
# ==============================================================================

print("=" * 70)
print("Checking gPhoto2 configuration...")
print("=" * 70)

print(f"gphoto2 binary : {GPHOTO2_BIN}")
print(f"LD_LIBRARY_PATH: {gphoto_env['LD_LIBRARY_PATH']}")
print(f"CAMLIBS        : {gphoto_env['CAMLIBS']}")
print(f"IOLIBS         : {gphoto_env['IOLIBS']}")

if not GPHOTO2_BIN.exists():
    raise FileNotFoundError(
        f"gphoto2 executable not found at:\n{GPHOTO2_BIN}"
    )

if not CAMLIBS.exists():
    raise FileNotFoundError(
        f"CAMLIBS directory not found at:\n{CAMLIBS}"
    )

if not IOLIBS.exists():
    raise FileNotFoundError(
        f"IOLIBS directory not found at:\n{IOLIBS}"
    )

# Check actual gPhoto2/libgphoto2 versions
version_check = subprocess.run(
    [str(GPHOTO2_BIN), "--version"],
    env=gphoto_env,
    capture_output=True,
    text=True,
)

print()

if version_check.stdout:
    print(version_check.stdout)

if version_check.returncode != 0:
    if version_check.stderr:
        print(version_check.stderr)

    raise RuntimeError(
        "Unable to start gphoto2 using the configured libraries."
    )

# ==============================================================================
# VERIFY CAMERA
# ==============================================================================

print("=" * 70)
print("Checking camera...")
print("=" * 70)

camera_check = subprocess.run(
    [str(GPHOTO2_BIN), "--auto-detect"],
    env=gphoto_env,
    capture_output=True,
    text=True,
)

print(camera_check.stdout)

if camera_check.returncode != 0:
    print(camera_check.stderr)
    raise RuntimeError("gPhoto2 camera detection failed.")

if "Sony ILCE-7RM4A" not in camera_check.stdout:
    print("WARNING: Sony ILCE-7RM4A was not detected.")
    print("Check USB connection and PC Remote mode.")

# ==============================================================================
# PMU / CPU CYCLE COUNTER
# ==============================================================================

print("=" * 70)
print("Loading PMU module...")
print("=" * 70)

if not PMU_MODULE.exists():
    raise FileNotFoundError(
        f"PMU kernel module not found:\n{PMU_MODULE}"
    )

if not CC_LIBRARY.exists():
    raise FileNotFoundError(
        f"CPU cycle library not found:\n{CC_LIBRARY}"
    )

# Remove existing module if already loaded.
# Failure here is okay if the module was not already loaded.
subprocess.run(
    ["sudo", "rmmod", "pmu_el0_cycle_counter"],
    capture_output=True,
    text=True,
)

# Insert kernel module
pmu_result = subprocess.run(
    ["sudo", "insmod", str(PMU_MODULE)],
    capture_output=True,
    text=True,
)

if pmu_result.returncode != 0:
    print("PMU module warning:")
    print(pmu_result.stderr.strip())
else:
    print("PMU module loaded successfully.")

# Load CPU cycle counter shared library
print("Loading CPU cycle counter library...")

lib = ctypes.CDLL(str(CC_LIBRARY))
lib.read_cpu_cycle_counter.restype = ctypes.c_uint64

print("CPU cycle counter ready.")

# ==============================================================================
# INCLINOMETER
# ==============================================================================

def get_latest_inclinometer():
    """
    Return the newest available inclinometer sample as (pitch, roll).

    The inclinometer logger runs separately and continuously writes lines like:

        -9,12 captured on 2026-09-11 16:20:10 and at CPU cycle:...

    At the camera's calculated exposure midpoint, this function reads the
    newest completed sample from the newest results/inclinometer*/angles_times.txt.

    IMPORTANT:
    This gives the latest inclinometer sample AVAILABLE at the midpoint.
    The sensor sample itself may have been generated slightly before the
    exact midpoint, depending on the inclinometer output rate.
    """

    try:
        inclinometer_dirs = sorted(
            RESULTS_DIR.glob("inclinometer*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not inclinometer_dirs:
            print("WARNING: No inclinometer results directory found.")
            return None, None

        angle_file = inclinometer_dirs[0] / "angles_times.txt"

        if not angle_file.exists():
            print(f"WARNING: Inclinometer file not found: {angle_file}")
            return None, None

        # Read the newest valid measurement.
        with open(angle_file, "r") as f:
            lines = f.readlines()

        for line in reversed(lines):
            line = line.strip()

            if not line or line == "START:":
                continue

            # Keep only the raw two-angle part before " captured on ".
            angle_part = line.split(" captured on ", 1)[0].strip()
            values = [v.strip() for v in angle_part.split(",")]

            if len(values) < 2:
                continue

            first = float(values[0])
            second = float(values[1])

            if INCLINOMETER_VALUE_ORDER == "pitch_roll":
                pitch = first
                roll = second
            elif INCLINOMETER_VALUE_ORDER == "roll_pitch":
                roll = first
                pitch = second
            else:
                raise ValueError(
                    "INCLINOMETER_VALUE_ORDER must be "
                    "'pitch_roll' or 'roll_pitch'"
                )

            return pitch, roll

        print("WARNING: No valid inclinometer measurement found.")
        return None, None

    except Exception as e:
        print(f"WARNING: Could not read inclinometer: {e}")
        return None, None


# ==============================================================================
# OUTPUT SETUP
# ==============================================================================

image_index = 1

timestr = time.strftime("%Y%m%d-%H%M%S")

output_file_path = RESULTS_DIR / f"camera{timestr}"

output_file_path.mkdir(
    exist_ok=True,
    parents=True
)

output_file = output_file_path / "imgs_times.txt"

header = (
    "Image | "
    "T0_Trigger_UTC | "
    "T2_Complete_UTC | "
    "Midpoint_UTC | "
    "Midpoint_ms | "
    "Pitch | "
    "Roll | "
    "CPU_Cycle\n"
)

output_file.write_text(header)

print()
print("=" * 70)
print("MANNA Celestial Navigation Capture")
print("=" * 70)
print(f"Exposure time : {EXPOSURE_SECONDS} seconds")
print(f"Saving images : {output_file_path}")
print(f"Logging to    : {output_file}")
print("Press Ctrl+C to stop")
print()

# ==============================================================================
# MAIN CAPTURE LOOP
# ==============================================================================

try:

    while True:

        print()
        print("=" * 70)
        print(f"=== Capture {image_index} ===")
        print("=" * 70)

        image_path = output_file_path / f"img{image_index}.ARW"

        # ======================================================================
        # T0 - TRIGGER COMMAND TIMESTAMP
        # ======================================================================

        T0_time = datetime.datetime.now(
            datetime.timezone.utc
        )

        # Matching monotonic timestamp for precise short-duration waiting.
        T0_monotonic = time.monotonic()

        T0_ms = int(
            T0_time.timestamp() * 1000
        )

        T0_str = T0_time.strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3] + " UTC"

        print()
        print(f"T0 (Trigger): {T0_str}")
        print(
            f"Capturing ({EXPOSURE_SECONDS}s exposure)..."
        )

        # ======================================================================
        # CAPTURE IMAGE + SAMPLE INCLINOMETER AT CALCULATED MIDPOINT
        # ======================================================================

        midpoint_seconds = EXPOSURE_SECONDS / 2.0

        midpoint_time = (
            T0_time
            + datetime.timedelta(
                seconds=midpoint_seconds
            )
        )

        midpoint_str = midpoint_time.strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3] + " UTC"

        midpoint_ms = int(
            T0_ms
            + (EXPOSURE_SECONDS * 500.0)
        )

        # Use the monotonic T0 captured above so wall-clock adjustments
        # do not affect the short midpoint wait.
        process = subprocess.Popen(
            [
                str(GPHOTO2_BIN),
                "--capture-image-and-download",
                "--force-overwrite",
                f"--filename={image_path}",
            ],
            env=gphoto_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait until the calculated exposure midpoint:
        # T0 + EXPOSURE_SECONDS / 2
        target_monotonic = T0_monotonic + midpoint_seconds
        remaining = target_monotonic - time.monotonic()

        if remaining > 0:
            time.sleep(remaining)

        # ======================================================================
        # MIDPOINT - READ LATEST AVAILABLE PITCH / ROLL
        # ======================================================================

        pitch, roll = get_latest_inclinometer()

        print(f"Midpoint Pitch: {pitch}")
        print(f"Midpoint Roll : {roll}")

        # Wait for gPhoto2 capture/download to complete.
        try:
            stdout, stderr = process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise

        returncode = process.returncode

        # ======================================================================
        # T2 - COMMAND COMPLETE / IMAGE DOWNLOADED
        # ======================================================================

        T2_time = datetime.datetime.now(
            datetime.timezone.utc
        )

        T2_ms = int(
            T2_time.timestamp() * 1000
        )

        T2_str = T2_time.strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )[:-3] + " UTC"

        # ======================================================================
        # SUCCESS
        # ======================================================================

        if returncode == 0:

            # CPU cycle count
            end_cycle = (
                lib.read_cpu_cycle_counter()
            )

            # ==============================================================
            # LOG
            # ==============================================================

            log_entry = (
                f"img{image_index} | "
                f"{T0_str} | "
                f"{T2_str} | "
                f"{midpoint_str} | "
                f"{midpoint_ms} | "
                f"{pitch} | "
                f"{roll} | "
                f"{end_cycle}\n"
            )

            with open(
                output_file,
                "a"
            ) as f:
                f.write(log_entry)

            # ==============================================================
            # DISPLAY RESULT
            # ==============================================================

            print()
            print(f"T2 (Complete): {T2_str}")

            print()
            print(
                "✓ MIDPOINT "
                "(use for GAST/longitude): "
                f"{midpoint_str}"
            )

            print(
                f"  Midpoint (ms): {midpoint_ms}"
            )

            print(
                f"  Pitch:         {pitch}"
            )

            print(
                f"  Roll:          {roll}"
            )

            print(
                f"  CPU cycle:     {end_cycle}"
            )

            print(
                f"  File:          {image_path}"
            )

            if stdout.strip():
                print()
                print("gphoto2 output:")
                print(stdout.strip())

            image_index += 1

            time.sleep(1)

        # ======================================================================
        # CAPTURE FAILURE
        # ======================================================================

        else:

            print()
            print("✗ Capture FAILED!")

            print(
                f"Return code: {returncode}"
            )

            if stdout.strip():
                print()
                print("gphoto2 stdout:")
                print(stdout.strip())

            if stderr.strip():
                print()
                print("gphoto2 stderr:")
                print(stderr.strip())

            time.sleep(2)

# ==============================================================================
# GRACEFUL SHUTDOWN
# ==============================================================================

except KeyboardInterrupt:

    print()
    print()
    print("=" * 70)
    print("=== CAPTURE STOPPED ===")
    print("=" * 70)

    print(
        f"Total captures: {image_index - 1}"
    )

    print(
        f"Images saved to: {output_file_path}"
    )

    print(
        f"Log file: {output_file}"
    )

    print()
    print("Log file contents:")
    print("=" * 70)

    if output_file.exists():
        print(
            output_file.read_text()
        )

    print("=" * 70)

# ==============================================================================
# TIMEOUT
# ==============================================================================

except subprocess.TimeoutExpired:

    print()
    print(
        "✗ ERROR: gphoto2 capture "
        "timed out after 60 seconds."
    )

# ==============================================================================
# OTHER ERRORS
# ==============================================================================

except Exception as e:

    print()
    print(f"✗ ERROR: {e}")

