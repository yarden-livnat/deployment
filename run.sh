#!/usr/bin/env bash

echo Running $1 samples using $2 jobs

for j in $(seq 1 $2); do
    mkdir -p simulations/$j
    python -m scenario -t eg01-eg23-simple.xml -n $1 -j $j &
done
