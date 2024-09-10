#!/bin/bash
while true; do
  git add .
  git commit -m "Auto Commit"
  git push
  sleep 300
done
