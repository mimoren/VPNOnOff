#!/usr/bin/env python3
"""ADB integration check; requires a debug APK, configured SFA, and active monitoring.

Temporarily toggles WiFi, restarts VPN OnOff, and restores the original WiFi state.
Uses the real SFA app and Shizuku; never creates or changes VPN profiles.
"""

import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--serial", required=True, help="USB or emulator adb device serial")
parser.add_argument("--package", default="com.vpnonoff", help="installed debug application ID")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", args.package):
    parser.error("Invalid Android application ID")
if ":" in args.serial:
    parser.error("WiFi cycling disconnects wireless ADB. Use USB or a phone-local check with an independent WiFi restoration guard.")
adb = ["adb", "-s", args.serial]


def run(*command):
    result = subprocess.run(adb + list(command), capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def foreground():
    return "isForeground=true" in run(
        "shell", "dumpsys", "activity", "services", "io.nekohasekai.sfa/.bg.VPNService"
    )


def connected():
    if not foreground():
        return False
    state = run("shell", "dumpsys", "vpn_management")
    return ("Active package name: io.nekohasekai.sfa" in state
            and "Active vpn type: 1" in state)


def wait_for(check, message):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if check():
            print("PASS:", message, flush=True)
            return
        time.sleep(0.5)
    raise RuntimeError("Timed out: " + message)


prefs = ET.fromstring(run("shell", "run-as", args.package, "cat",
                          "shared_prefs/vpnonoff_prefs.xml"))
values = {node.get("name"): node.get("value") for node in prefs}
if values.get("selected_client") != "5" or values.get("service_enabled") != "true":
    raise RuntimeError("Select sing-box (SFA), authorize Shizuku, and start monitoring first")
if "io.nekohasekai.sfa" not in run("shell", "pm", "path", "io.nekohasekai.sfa"):
    raise RuntimeError("Official SFA is not installed")
if "mIsShowing=true" in run("shell", "dumpsys", "window", "policy"):
    raise RuntimeError("Unlock the device before running this check")

original_wifi = run("shell", "settings", "get", "global", "wifi_on").strip()
if original_wifi not in ("0", "1"):
    raise RuntimeError("Cannot determine original WiFi state")

try:
    # Reproduce startup with a WIFI-backed VPN already running. VPN networks
    # must not survive as phantom WiFi entries after the initial disconnect.
    run("shell", "svc", "wifi", "enable")
    wait_for(lambda: "Wifi is connected to" in run("shell", "cmd", "wifi", "status"),
             "device connected to saved WiFi")
    run("shell", "am", "force-stop", args.package)
    if not foreground():
        tile = "io.nekohasekai.sfa/.bg.TileService"
        run("shell", "cmd", "statusbar", "add-tile", tile)
        run("shell", "cmd", "statusbar", "expand-settings")
        run("shell", "cmd", "statusbar", "click-tile", tile)
        wait_for(connected, "SFA VPN active over WiFi before monitor startup")
    run("shell", "cmd", "statusbar", "collapse")
    run("shell", "am", "start", "-W", "-n", f"{args.package}/com.vpnonoff.MainActivity")
    wait_for(lambda: not foreground(), "monitor startup stops an existing VPN on WiFi")
    for cycle in range(1, 3):
        run("shell", "svc", "wifi", "disable")
        wait_for(connected, f"cycle {cycle}: WiFi off starts the real SFA VPN")
        # Process recovery must not toggle an already running SFA off.
        if cycle == 1:
            run("shell", "am", "force-stop", args.package)
            run("shell", "am", "start", "-W", "-n", f"{args.package}/com.vpnonoff.MainActivity")
            wait_for(lambda: "isForeground=true" in run(
                "shell", "dumpsys", "activity", "services", f"{args.package}/com.vpnonoff.WifiMonitorService"
            ), "monitor recovers from process restart")
            # Observe beyond the start-command timeout, not just the old VPN state.
            time.sleep(6)
            if not connected():
                raise RuntimeError("Restarting the monitor toggled SFA off")
            print("PASS: monitor restart preserves the existing SFA VPN", flush=True)
        run("shell", "svc", "wifi", "enable")
        wait_for(lambda: not foreground(), f"cycle {cycle}: WiFi on stops SFA")
    print("PASS: SFA integration checks completed", flush=True)
finally:
    run("shell", "cmd", "statusbar", "collapse")
    run("shell", "svc", "wifi", "enable" if original_wifi == "1" else "disable")
    run("shell", "am", "start", "-W", "-n", f"{args.package}/com.vpnonoff.MainActivity")
