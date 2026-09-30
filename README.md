# USB Phone Control (Android via scrcpy)

This project lets you control an Android phone from your PC using [scrcpy](https://github.com/Genymobile/scrcpy) — over **USB** or **Wi-Fi (wireless debugging)** — with a simple Windows GUI or PowerShell scripts.

> **iPhone (iOS) note:** This project is for **Android**. On iPhone/iOS there is no widely supported, reliable equivalent to `scrcpy` that provides full USB control (mouse/keyboard input) from a PC.

## Features

- Desktop GUI (`phone_control_ui.py`) with one-click buttons for everything
- Mirrors your phone screen and lets you control it with your mouse and keyboard
- Hears your phone's **audio on the PC** — video + audio are forwarded together, like a camera feed (choose the source in the GUI: phone audio, microphone, or off)
- USB connection support
- Wireless debugging (Wi-Fi) support, including **pairing code** and **QR code** pairing
- Bundled `adb` and `scrcpy` binaries - `setup.ps1` always downloads the **latest** versions (scrcpy v4.x, newest platform-tools), so no manual install is needed

## Requirements

- Windows PC with **PowerShell**
- Android phone
- USB cable (data-capable)
- **Python 3.10 or newer** installed and available as `py` or `python` (only needed for the GUI and QR pairing)
- On the phone: **Developer options** and **USB debugging** enabled (see Troubleshooting below)

## Quick start (USB)

1. Run setup to download `adb` and `scrcpy`:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\setup.ps1
   ```

2. Plug in your phone over USB and verify it is detected (accept the "Allow USB debugging?" prompt on the phone):

   ```powershell
   .\scripts\check-device.ps1
   ```

3. Start controlling the phone:

   ```powershell
   .\scripts\run.ps1
   ```

   A window with your phone's screen opens — click and type to control it. Close that window (or press `Ctrl+C`) when done.

## Option A: Use the GUI app (recommended)

The GUI gives you buttons for setup, device check, starting/stopping scrcpy, wireless pairing, and more — no need to remember commands.

### Start the GUI

**Double-click** `start-ui.ps1` in File Explorer, or run it from PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start-ui.ps1
```

Alternatively, run the Python file directly:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
py -3 .\phone_control_ui.py
```

The window opens with a **log panel** at the bottom that shows the output of every command you run.

### Use the GUI

| Button | What it does |
| --- | --- |
| **Setup (download tools)** | Downloads and extracts `adb` (platform-tools) and `scrcpy` into `tools\`. Run this first. |
| **Check device** | Shows whether your phone is detected over USB/Wi-Fi (`adb devices -l`). |
| **Start scrcpy** | Launches scrcpy (mirror + control). If you entered a **Connect IP:port** in the wireless section, it connects over Wi-Fi with lag-reduced settings; otherwise it uses USB. |
| **Stop scrcpy** | Closes the running scrcpy window. |
| **Clear log** | Clears the log panel. |
| **Audio** dropdown | Selects what is forwarded to your PC: **Phone audio** (default) plays the phone's sound; **Microphone** captures the phone's mic and plays it on the PC (acts as a remote mic — the phone may ask to allow mic recording); **Off** disables audio to save bandwidth on slow Wi-Fi. |
| **Quit** | Closes the app (also stops scrcpy if it is running). |

**Wireless debugging section** (see the Wireless guide below for the phone steps):

| Field / Button | What it does |
| --- | --- |
| **Pair IP:port** + **Code** + **Pair** | Pairs the PC with the phone (`adb pair`) using the IP:port and 6-digit code shown on the phone. |
| **Connect IP:port** + **Connect** | Connects adb to the phone over Wi-Fi (`adb connect`). |
| **Disconnect** | Disconnects adb from the phone. |
| **Status** | Lists connected devices. |
| **Install Lyto** | Installs `lyto`, a helper for QR-code pairing (requires internet). |
| **QR Pair (Lyto)** | Opens a window showing a QR code to scan from the phone (Wireless debugging > Pair device with QR code). |
| **Quick connect** | Runs **Pair → Connect → Start scrcpy** in one click using the fields above. Pairing is skipped if the Pair fields are empty. |

## Option B: Use the PowerShell scripts

Each script lives in `scripts\`. From the project root, run:

| Task | Command |
| --- | --- |
| Download tools (`adb` + `scrcpy`) | `.\scripts\setup.ps1` |
| Check if the phone is detected | `.\scripts\check-device.ps1` |
| Start scrcpy (USB) | `.\scripts\run.ps1` |
| Start scrcpy over Wi-Fi | `.\scripts\run.ps1 -Serial "192.168.1.23:42593"` |
| Start scrcpy without audio | `.\scripts\run.ps1 -NoAudio` |
| Start scrcpy using the phone's mic as a remote mic | `.\scripts\run.ps1 -AudioSource mic` |
| Guided wireless setup (pair + connect + run) | `.\start-wireless.ps1` |

(Prepend `Set-ExecutionPolicy -Scope Process Bypass` before any script if PowerShell blocks it, e.g. `Set-ExecutionPolicy -Scope Process Bypass; .\scripts\setup.ps1`.)

## Wireless (no cable)

Your phone and PC must be on the **same Wi-Fi network**.

On your phone:

- Settings
- Developer options
- Enable **Wireless debugging**

### Pair (pairing code)

1. On the phone: Wireless debugging > **Pair device with pairing code**
2. Note the **IP:port** and the 6-digit **pairing code** shown on the phone
3. On the PC:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\wireless-pair.ps1 -PairHostPort "IP:PORT" -PairingCode "123456"
   ```

### Pair (QR code, via lyto)

1. On the PC, install the QR helper once: `.\scripts\install-lyto.ps1` (needs internet)
2. Run `.\scripts\lyto-qr.ps1` — a window with a QR code opens
3. On the phone: Wireless debugging > **Pair device with QR code**, then scan the code

### Connect

1. On the phone (Wireless debugging main screen): note the **IP:port** listed there (often a different port than the pairing screen)
2. On the PC:

   ```powershell
   .\scripts\wireless-connect.ps1 -HostPort "IP:PORT"
   ```

### Start scrcpy over Wi-Fi

```powershell
.\scripts\run.ps1 -Serial "IP:PORT"
```

> The `-Serial` flag enables Wi-Fi-friendly settings (max size 1024, 2 Mbps bitrate, 30 FPS) to reduce lag. **Audio is forwarded by default** — pick the source with `-AudioSource` (`output`, `playback`, `mic`, `voice-performance`), disable it with `-NoAudio`, or lower its bitrate with `-AudioBitRate "64K"` to save bandwidth.

Or use the all-in-one interactive helper:

```powershell
.\start-wireless.ps1
```

### Disconnect (optional)

```powershell
.\scripts\wireless-disconnect.ps1 -HostPort "IP:PORT"
```

(Without `-HostPort` it disconnects all wireless devices.)

### Check wireless status

```powershell
.\scripts\wireless-status.ps1
```

## Project structure

```
USB Phone Control/
├── phone_control_ui.py        # The GUI app (Python/tkinter)
├── start-ui.ps1               # Launcher for the GUI
├── start-wireless.ps1         # Guided wireless setup (pair + connect + run)
├── scripts/                   # Individual PowerShell scripts
│   ├── setup.ps1              # Downloads adb + scrcpy into tools\
│   ├── check-device.ps1       # adb devices -l
│   ├── run.ps1                # Starts scrcpy (USB or -Serial for Wi-Fi)
│   ├── wireless-pair.ps1      # adb pair
│   ├── wireless-connect.ps1   # adb connect
│   ├── wireless-disconnect.ps1# adb disconnect
│   ├── wireless-status.ps1    # adb devices -l
│   ├── install-lyto.ps1       # Installs the QR pairing helper (lyto)
│   └── lyto-qr.ps1            # Opens a QR code window for pairing
└── tools/                     # Bundled binaries (created by setup.ps1)
    ├── platform-tools/        # adb.exe
    └── scrcpy/                # scrcpy.exe
```

> The `tools\` folder (and Python `__pycache__`) is not stored in this repository — `setup.ps1` downloads everything it needs on first run.

## Troubleshooting

### setup.ps1 downloads are slow or stall

- `setup.ps1` fetches scrcpy and platform-tools from Google and GitHub. On a slow connection a download may take a while; the script now fails after 10 minutes instead of hanging forever.
- Retry later, or run the script again - it always re-downloads the **latest** versions and overwrites `tools\`.

### Phone not detected by ADB

- **Use a data-capable cable** (some cables are charge-only).
- **Unlock the phone** and reconnect the cable.
- **Enable USB debugging**:
  - Settings
  - About phone
  - Tap Build number 7 times (Developer options)
  - Developer options
  - Enable USB debugging
- **Install the correct USB driver** (common on Windows):
  - Google USB Driver (Pixel)
  - Samsung USB Driver (Samsung)
  - OEM driver for your brand

Then run:

```powershell
.\scripts\check-device.ps1
```

### Device shows as "unauthorized"

- Look at your phone and accept the **RSA/USB debugging authorization** prompt.
- If you missed it, revoke and retry:
  - Developer options
  - Revoke USB debugging authorizations
  - Reconnect cable and accept prompt

### ADB is stuck / wrong ADB is being used

This project ships its own `adb.exe` under `tools\platform-tools`. If you have other ADB installs, you can restart ADB:

```powershell
tools\platform-tools\adb.exe kill-server
tools\platform-tools\adb.exe start-server
tools\platform-tools\adb.exe devices -l
```

### scrcpy opens then immediately closes

- Run `check-device.ps1` and ensure a device is listed.
- Try a different USB port.
- If your device is in "File transfer" / "MTP" mode, keep it there.

### No audio from the phone

- Make sure the **Audio** dropdown in the GUI isn't set to **Off** (or run `run.ps1` without `-NoAudio`).
- Audio forwarding needs **Android 11 or newer** (Android 10 and older can't forward audio; the log will say so). On Android 11, keep the phone unlocked when starting scrcpy.
- scrcpy plays the phone's audio through your **Windows default playback device** (speakers/headphones). Check that the right device is selected in Windows Sound settings.
- The phone's speaker is muted while mirroring — that's normal; audio goes to the PC instead.
- If the log shows a warning that audio capture failed (some devices refuse it), scrcpy continues with **video only** — `--require-audio` is intentionally not used so mirroring never fails because of audio.
- When **Microphone** is selected, the phone may show a mic-in-use indicator while its mic is being used (Android 11+). The mic audio plays through your **default playback device** (speakers) — hearing your own mic can cause feedback, so use headphones.
- scrcpy alone **plays the phone's mic on your speakers**; to use the phone's mic *as your PC's microphone* in other apps (e.g. Zoom/Teams), you need a virtual audio cable (like VB-Cable) to route scrcpy's audio output into the PC's mic input.

### GUI won't start ("Python not found")

- Install **Python 3.10 or newer** from python.org and make sure **"Add python.exe to PATH"** is checked during installation, or that the `py` launcher is available.
- Then retry `.\start-ui.ps1`.
