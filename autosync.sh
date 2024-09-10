#!/bin/bash

while true; do
  git pull origin main --rebase
  git .add
  git commit -m "Auto Commit"
  git push origin main
  sleep 300
done
