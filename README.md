# Screen Text Monitor & Alert System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-Image%20Processing-green.svg)
![Tesseract](https://img.shields.io/badge/OCR-Tesseract-yellow.svg)
![ntfy](https://img.shields.io/badge/Alerts-ntfy.sh-orange.svg)

A desktop screen monitoring tool built with Python and Tkinter. It continuously captures a targeted screen region, performs real-time Optical Character Recognition (OCR) using Tesseract, and triggers both local audio alerts and instant push notifications to your mobile phone via `ntfy.sh`.

Designed with a thread-safe architecture to prevent GUI lockups while running screen processing asynchronously.

---

## Features

- **Auto-Minimizing Region Selection:** Click a single button to auto-minimize the app and drag a selection bounding box over any desktop area.
- **Custom Text Triggers:** Enter any specific text string to monitor (e.g., *"In combat"*, *"Warning"*, *"Low Health"*).
- **Instant Phone Push Notifications:** Integrates with `ntfy.sh` for high-priority mobile alerts.
- **Local Sound Alarms:** Plays customizable asynchronous audio alerts upon detection.
- **Live Debug Console:** Features a thread-safe event and error logger directly inside the GUI interface.
- **Time Delay:** User has the ability to set the time, of how long the detected text is on screen before sending notification.
---

## Prerequisites

### 1. Python 3.10+
Ensure Python is installed on your system.
> **Note for Windows users:** Make sure to check **"Add python.exe to PATH"** during installation.

### 2. Tesseract OCR Engine
Install the Tesseract OCR engine for Windows:
1. Download the installer from the [UB Mannheim Tesseract Repository](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install it to the default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
*(If installed to a different location, update the `tesseract_cmd` variable at the top of the script).*

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DemiG33k/mir4-monitor.git
   cd mir4-monitor
