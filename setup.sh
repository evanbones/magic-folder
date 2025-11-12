#!/bin/bash

echo "--- Magic Folder Setup ---"
echo "This script will securely configure your WSL/Ubuntu environment to"
echo "mount your network drive."
echo

read -p "Enter your network username: " SMB_USER
read -s -p "Enter your network password: " SMB_PASS
echo

LOCAL_MOUNT="/mnt/vpoho_scratch"
NETWORK_PATH="//192.168.0.5/Scratch"
SMB_DOMAIN="BOSS"

echo "--- 1. Installing required network tools (cifs-utils) ---"
sudo apt-get update
sudo apt-get install -y cifs-utils

echo "--- 2. Creating mount point at $LOCAL_MOUNT ---"
sudo mkdir -p $LOCAL_MOUNT

echo "--- 3. Testing credentials (temporary mount) ---"
sudo mount -t cifs "$NETWORK_PATH" "$LOCAL_MOUNT" -o username="$SMB_USER",password="$SMB_PASS",domain="$SMB_DOMAIN"

if [ $? -ne 0 ]; then
    echo
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "ERROR: Mount failed. Credentials or server path are bad."
    echo "Please check your username/password and try again."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    sudo umount "$LOCAL_MOUNT" &> /dev/null
    exit 1
fi

echo "Credentials are valid! Proceeding with permanent setup."
sudo umount "$LOCAL_MOUNT"

echo "Writing credentials to /etc/win-credentials..."
echo "username=$SMB_USER" | sudo tee /etc/win-credentials > /dev/null
echo "password=$SMB_PASS" | sudo tee -a /etc/win-credentials > /dev/null
echo "domain=$SMB_DOMAIN" | sudo tee -a /etc/win-credentials > /dev/null
sudo chmod 600 /etc/win-credentials
echo "Credentials file created and locked."

echo "Adding mount to /etc/fstab..."
USER_UID=$(id -u)
USER_GID=$(id -g)

FSTAB_LINE="$NETWORK_PATH $LOCAL_MOUNT cifs credentials=/etc/win-credentials,uid=${USER_UID},gid=${USER_GID},iocharset=utf8 0 0"

if ! grep -qF "$FSTAB_LINE" /etc/fstab; then
    echo -e "\n# Mount for Magic Folder" | sudo tee -a /etc/fstab > /dev/null
    echo "$FSTAB_LINE" | sudo tee -a /etc/fstab > /dev/null
    echo "fstab configured."
else
    echo "fstab entry already exists."
fi

echo "Attempting to mount the drive now..."
sudo mount -a

if ls "$LOCAL_MOUNT" &> /dev/null; then
    echo "--------------------------------------------------------"
    echo "SUCCESS! The network drive is permanently mounted."
    echo "You can now exit this Ubuntu terminal."
    echo "Run your 'docker build' and 'docker run' commands from PowerShell."
    echo "--------------------------------------------------------"
else
    echo "ERROR! Could not mount the drive using fstab."
    echo "Please check /etc/fstab and /etc/win-credentials."
fi