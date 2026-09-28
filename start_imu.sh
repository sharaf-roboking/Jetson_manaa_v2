#!/bin/bash

foldername=$(date +%Y%m%d%H%M%S)

mkdir -p "./results/imu/$foldername"

sudo ./ustrain/7_series_stream_imu_example_c \
    > "./results/imu/$foldername/ustrain.txt"
