# 📱 Android Termux Deployment & User Guide

This guide walks you through installing and running **IPO Radar Intelligence** on an Android phone using **Termux** in **Lightweight Local Mode**.

---

## 1. Prerequisites on Android

1. **Install Termux from F-Droid**:
   - Download the latest Termux APK from [F-Droid](https://f-droid.org/packages/com.termux/).
   - *(Note: Do NOT install from Google Play Store; the Play Store version is discontinued and packages will fail to update).*
2. **Grant Storage Permission**:
   Open Termux and run:
   ```bash
   termux-setup-storage
   ```
   Tap **Allow** when prompted.

---

## 2. Automated Installation

Run the following commands inside Termux:

```bash
# 1. Update Termux packages
pkg update -y && pkg upgrade -y

# 2. Install Git & Python
pkg install -y git python clang libjpeg-turbo libpng build-essential

# 3. Clone or navigate to your ipo-radar folder
# (If copied to Android Downloads, navigate with: cd /sdcard/Download/ipo-radar-main/ipo-radar-main)
cd ~/ipo-radar-main

# 4. Run the automated Termux setup script
bash scripts/setup_termux.sh
```

The script will:
- Create a local virtual environment (`.venv_termux`)
- Install lightweight, mobile-optimized dependencies from `requirements-termux.txt`
- Initialize the local zero-config SQLite database (`backend/rhp.db`)

---

## 3. Starting the Platform

To start both the **FastAPI REST API** and the **Streamlit Research Dashboard**:

```bash
bash scripts/start_termux.sh
```

You will see:
```text
==========================================================
🎯 Starting IPO Radar Research Intelligence on Android Termux
==========================================================
-> Launching FastAPI Backend on http://127.0.0.1:8000...
-> Launching Streamlit Research Terminal on http://127.0.0.1:8501...
-> Open your mobile browser and navigate to: http://127.0.0.1:8501
==========================================================
```

### Accessing the Dashboard:
Open Google Chrome, Brave, or your preferred browser on your phone and open:
👉 **`http://127.0.0.1:8501`**

To stop the servers, simply press `Ctrl + C` in Termux.

---

## 4. Mobile Architecture & Resource Optimizations

- **Zero Docker Requirement**: Uses local SQLite and pure-Python search algorithms.
- **Pure-Python BM25 & Lightweight Vectors**: Avoids heavy C++ compilation or FAISS crashes on ARM mobile processors.
- **Local Document Storage**: All downloaded and uploaded prospectuses stay on your device in `storage/raw_documents/`.
- **Low Memory Footprint**: Runs comfortably in under 350 MB of RAM.

---

## 5. Troubleshooting in Termux

- **Issue: `python: command not found`**
  - Run: `pkg install python -y`
- **Issue: Pillow / Image compilation error**
  - Run: `pkg install libjpeg-turbo libpng -y && pip install pillow`
- **Issue: Port 8000 or 8501 already in use**
  - Run: `fuser -k 8000/tcp 8501/tcp` to terminate any hanging background processes.

