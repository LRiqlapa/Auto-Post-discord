# Auto-post

This project auto-posts messages to Discord channels with interval and optional webhook logging.

original source: https://github.com/lantas-bit/Auto-post

> Warning: This tool breaks Discord Terms of Service. Use at your own risk. I’m not responsible for any bans or consequences.

[My Discord Server](https://discord.com/invite/psdQaVEnHt)

[Lantas Discord Server](https://discord.com/invite/M9cD8ZC5m8)

## Setup Instructions on termux

**Install Termux:**
[Download Termux here](https://f-droid.org/en/packages/com.termux/)


**Clone the repo & install requirements:**
```bash
pkg update
pkg install git
pkg install python -y
git clone https://github.com/LRiqlapa/Auto-Post-discord
cd Auto-Post-discord
pip install flask requests
```

**Run the bot:**
```bash
python autopost.py
```
**How to get discord account token?**

[How to get token on pc](https://youtu.be/LnBnm_tZlyU?si=J3wSpuRaXqI5ycUj)

[How to get token on kiwi browser (android)](https://youtu.be/OvOKuKZwuwQ?si=LCoqhtTlKJv74VxG)

**Open in browser:**

Visit `http://localhost:5000` from your phone browser (while Termux is running).

## Setup Instructions on windows

**Install Python**

Download from: 
[Python](https://python.org)

**During installation, make sure to check “Add Python to PATH”**


**Download / clone the repository**

**[Download this repository]**
- Click the green `Code` button
- Choose **Download Zip**
- Extract the file zip

**[Cloning this repositori] Open CMD and run:**

**Install git:**
[Git](https://git-scm.com/downloads)

```bash
git clone https://github.com/LRiqlapa/Auto-Post-discord
cd Auto-Post-discord
```
**Before installing required packages on cmd or powershell read this:**

_if you already download and extract the Zip file run this on cmd inside the extracted folder_

**Install required packages**
```bash
pip install flask requests
```

**Run the bot**
```bash
python autopost.py
```


**Access the web controller**
Open your browser and visit:

```http://localhost:5000```

# Screenshot
<img width="440" height="300" alt="Screenshot (440)" src="https://github.com/user-attachments/assets/9b79e2ca-ce02-4ab6-b3a9-1214c516e2eb" />

<img width="300" height="600" alt="Screenshot (440)" src="https://github.com/user-attachments/assets/42a09478-cd4c-4328-bc3d-cc37164c8010" />



