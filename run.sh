#!/usr/bin/env bash

echo Running $1 samples using $2 jobs

for j in $(seq 1 $2); do
    mkdir -p simulations/$j
    python -m scenario -t Transition_scenario.xml -n $1 -j $j &
done
