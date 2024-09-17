#!/bin/bash 

cd $( dirname -- "$0"; )
for ((i=1; i<=1000; i++)); do
    python ./Main.py $i
    sleep 30s
done

read -p "Press enter to continue"