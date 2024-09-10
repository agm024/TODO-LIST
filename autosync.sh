#!/bin/bash

while true; do
  git add .
  git commit -m "Auto Commit"
  git pull origin main --rebase
  git push origin main
  sleep 60
done
