#!/bin/bash

echo "--- Magic Folder Setup ---"
echo "This script will securely configure your WSL/Ubuntu environment to"
echo "mount your network drive."
echo

read -p "Enter your network username: " SMB_USER
read -s -p "Enter your network password: " SMB_PASS
echo

LOCAL_MOUNT="/mnt/vpoho_scratch"

echo "Installing required network tools (cifs-utils) ---"
sudo apt-get update
sudo apt-get install -y cifs-utils

echo "Writing credentials to /etc/win-credentials..."
echo "username=$SMB_USER" | sudo tee /etc/win-credentials > /dev/null
echo "password=$SMB_PASS" | sudo tee -a /etc/win-credentials > /dev/null
echo "domain=BOSS" | sudo tee -a /etc/win-credentials > /dev/null
sudo chmod 600 /etc/win-credentials
echo "Credentials file created and locked."

echo "Creating mount point at $LOCAL_MOUNT..."
sudo mkdir -p $LOCAL_MOUNT

echo "Adding mount to /etc/fstab..."
USER_UID=$(id -u)
USER_GID=$(id -g)

FSTAB_LINE="//VPOHO/Scratch ${LOCAL_MOUNT} cifs credentials=/etc/win-credentials,uid=${USER_UID},gid=${USER_GID},iocharset=utf8 0 0"

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
    echo "SUCCESS! The network drive is mounted."
    echo "You can now exit this Ubuntu terminal and run your 'docker build' and 'docker run' commands from PowerShell."
else
    echo "ERROR! Could not mount the drive. Please check your credentials and server details in /etc/win-credentials and /etc/fstab, then run 'sudo mount -a' again."
fi