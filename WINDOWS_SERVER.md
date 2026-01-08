# Installation Guide: Magic Folder on Windows Server

This guide details how to deploy the **Magic Folder** automation on **Windows Server 2019/2022** using **WSL 2**. 

---

## Part 1: Server Prerequisites

### 1. Enable WSL 2
Open **PowerShell** as Administrator and run:

```powershell
wsl --install

```

* **Restart the server** when prompted.
* After rebooting, the installation should resume automatically. If prompted, create a **UNIX username** and **password** for your Ubuntu instance.


### 2. Install Docker Engine (Inside WSL)

1. Open your **Ubuntu** terminal.
2. Run the following block to install Docker:
```bash
# Update and install certificates
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg lsb-release -y

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL [https://download.docker.com/linux/ubuntu/gpg](https://download.docker.com/linux/ubuntu/gpg) | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] [https://download.docker.com/linux/ubuntu](https://download.docker.com/linux/ubuntu) \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

```


### 3. Configure Auto-Start

By default, Docker will not start when the server boots. Follow these steps to ensure persistence.

**Step A: Enable Docker Systemd in WSL**

1. Enable the service: `sudo systemctl enable docker`
2. **Shutdown WSL** (from PowerShell on the host): `wsl --shutdown`

**Step B: Create Windows Boot Task**

1. Open **Task Scheduler** on Windows Server.
2. **Create Basic Task** -> Name: "Start WSL Docker".
3. Trigger: **When the computer starts**.
4. Action: **Start a program**.
* **Program:** `wsl.exe`
* **Arguments:** `-d Ubuntu`

5. Finish, then **Properties** of the new task:
* Check **"Run whether user is logged in or not"**.
* Check **"Run with highest privileges"**.
* Save (enter Windows credentials).


---

## Part 2: Application Deployment

### 1. Download Project

Clone or copy the `magic-folder` project directory to a location on the Windows Server (e.g., `C:\Apps\magic-folder`).

### 2. Configure Credentials

Navigate to the project folder and create a file named `.env` with the network credentials required to mount the shares.

**File:** `.env`

```ini
SMB_USER=YOUR_USERNAME
SMB_PASS=YOUR_PASSWORD
SMB_DOMAIN=YOUR_DOMAIN

```

### 3. Start the Application

1. Open your **Ubuntu Terminal**.
2. Navigate to the Windows folder. WSL mounts C: drive at `/mnt/c`.
```bash
cd /mnt/c/Apps/magic-folder

```


3. Build and Run:
```bash
sudo docker compose up -d --build

```



---

## Part 3: Verification & Maintenance

### Check Status

To verify the container is running and the network drive is mounted:

```bash
sudo docker logs -f magic-folder


### Common Commands

| Action | Command (inside WSL) |
| --- | --- |
| **Restart App** | `sudo docker compose restart` |
| **Stop App** | `sudo docker compose down` |
| **Update Code** | `sudo docker compose up -d --build` |
| **View Logs** | `sudo docker logs -f magic-folder` |
