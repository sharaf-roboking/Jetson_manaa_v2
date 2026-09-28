#!/bin/bash

cd "$(dirname "$0")"

export LD_LIBRARY_PATH="$HOME/.local/lib:$HOME/.local/lib/aarch64-linux-gnu"
export CAMLIBS="$HOME/.local/lib/libgphoto2/2.5.34.1"
export IOLIBS="$HOME/.local/lib/libgphoto2_port/0.12.2"

python3 ./camera/record-camera_v3.py
