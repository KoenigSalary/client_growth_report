# How to Run the Monthly Job (Multiple Easy Options)

You no longer need to use the terminal every month. Pick the option that's easiest for you.

---

## 🥇 Option A — Double-click `.app` in Finder (Recommended)

The repo now includes a real macOS app bundle: **`launchers/Client Growth Report.app`**

### One-time setup
1. Open **Finder**
2. Navigate to the project folder
3. Open the `launchers` folder
4. **Drag `Client Growth Report.app` to your `Applications` folder** (or to your Dock)

### Every monthly run
1. Open **Launchpad** (or click the Dock icon, or open from Applications)
2. Click **Client Growth Report**
3. A Terminal window opens automatically and runs the script
4. Type your OTP into the Chromium window when it appears
5. ☕ Walk away — report is emailed and committed to git

> **First-time only**: macOS may show a security warning ("can't be opened because Apple cannot check it for malicious software"). To allow it:
>   - Right-click the app → **Open** → click **Open** in the dialog
>   - Or go to **System Settings → Privacy & Security → "Open Anyway"**

---

## 🥈 Option B — Add the .sh to Dock for one-click access

1. In Finder, navigate to `launchers/`
2. Right-click `run_local_mac_linux.sh` → **Get Info**
3. In the "Open with" section, choose **Terminal** (click the dropdown)
4. Click **Change All...** (so all `.sh` files open in Terminal)
5. Now you can **drag `run_local_mac_linux.sh` to your Dock** and just click it

---

## 🥉 Option C — Just Double-click in Finder

After doing the "Open with → Terminal → Change All" step above, you can just **double-click `run_local_mac_linux.sh` in Finder** anytime. No terminal needed.

---

## 🔧 Option D — macOS Shortcut (advanced)

Use macOS Shortcuts app:
1. Open **Shortcuts** app
2. Click **+** to create a new shortcut
3. Add action: **Run Shell Script**
4. Paste:
   ```bash
   cd ~/path/to/client_growth_report && ./launchers/run_local_mac_linux.sh
   ```
5. Name it "Client Growth Report"
6. In Settings, enable "Show in menu bar" — now it's one click from anywhere

---

## 🐢 Option E — The terminal way (still works)

```bash
cd ~/path/to/client_growth_report
./launchers/run_local_mac_linux.sh
```

---

## 💡 Tip — Calendar reminder for the 14th

Open Apple Calendar and create a recurring event:
- **Title**: Run Client Growth Report
- **Every**: month, on the 14th, 10:00 AM
- **Alert**: 30 minutes before
- **URL**: Drag `Client Growth Report.app` into the event so clicking the calendar alert launches the app

That's the closest you'll get to fully-automated, given the OTP-on-every-login constraint.
