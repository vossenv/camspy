#!/usr/bin/env bash

fullInstall=false

while [[ $# -gt 0 ]]
do
key=$1
case $key in
    -f|--full-install)
        fullInstall=true
        shift
        shift
        ;;
    *)
        echo "Parameter '$1' not recognized"
        exit
        shift # past argument
        shift # past value
esac
done
set --

echo "FULL_INSTALL"  = "${fullInstall}"

ipaddresses=(
    "192.168.50.155:spypi-1"
    "192.168.50.175:spypi-2"
    "192.168.50.243:spypi-3"
#    "192.168.50.101:spypi-3"
)



username="carag"
echo $username@$1
dir="/home/$username/camspy"
#homedir="/home/$username"
distpath="./dist/."
env_path="$dir/.venv"
wheelname="$dir/camspy-0.0.1-py3-none-any.whl"

function setupDependencies() {
  echo "$username@$1"
  ssh $username@$1 "sudo apt update"
  ssh $username@$1 "sudo apt install python3-pip -y"
  ssh $username@$1 "sudo apt install python3-picamera2 libcap-dev ffmpeg -y"
}

function deployBash() {
    set -x

    echo "send files"
    scp -r $distpath $username@$1:$dir
    if $fullInstall; then
      ssh $username@$1 "echo "Creating directory $dir";  sudo mkdir -p $dir; sudo chmod 777 $dir;"
      if ssh $username@$1 test -d $env_path; then
        echo "Venv found at $env_path..."
      else
        echo "Venv not found! Creating $env_path..."
        ssh $username@$1 "python -m venv $env_path --system-site-packages"
      fi
      ssh $username@$1 "source $env_path/bin/activate; pip install $wheelname --upgrade --force-reinstall"
    else
      ssh $username@$1 "source $env_path/bin/activate; pip install $wheelname --upgrade --no-deps --force-reinstall"
    fi
    set +x
    echo "Deploy complete! SSH in and run"
}


for i in ${ipaddresses[@]}; do

    IFS=':' tokens=(${i});

    echo
    host=${tokens[0]}
#    nickname=${tokens[1]}
#    ssh-keygen -R $host

    echo "Setup for ${host}"
    args=($host)
    if $fullInstall; then
      setupDependencies "${args[@]}"
    fi
    deployBash "${args[@]}"
done


