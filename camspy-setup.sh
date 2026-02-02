#!/usr/bin/env bash

wheelname=camspy-0.0.1-py3-none-any.whl
username="carag"

dir="/home/$username/camspy"
homedir="/home/$username"
distpath="./dist/."
env_path="$dir/.venv"

function setupDependencies() {
  sudo apt update
  sudo apt install python3-pip -y
  sudo apt install python3-picamera2 libcap-dev ffmpeg -y
}

function setupWheel() {
    set -x
    echo "Creating directory $dir";  sudo mkdir -p $dir; sudo chmod 777 $dir;

    if test -d $dir; then
      echo "Venv found at $env_path..."
    else
      echo "Venv not found! Creating $env_path..."
      python -m venv $env_path --system-site-packages
    fi
    set +x
    echo "Deploy complete! SSH in and run"
}

 setupDependencies
 deployBash


