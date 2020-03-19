#!/usr/bin/env bash

echo Running $1 samples using jobs $2 - $3

for j in $(seq $2 $3); do
    mkdir -p simulations/$j
    python -m scenario -t eg01-eg23_no_storing_legacy.xml -n $1 -j $j &
done
