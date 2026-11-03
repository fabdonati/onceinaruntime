"""Read-only environment inventory. Unavailable commands remain explicit in JSON."""

import argparse
import datetime as dt
import json
import platform
import shutil
import subprocess
from pathlib import Path


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return {"command": args, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": args, "unavailable": str(error)}


def inventory():
    commands = [["clang++", "--version"], ["c++", "--version"],
                ["cmake", "--version"], ["make", "--version"],
                ["python3", "--version"]]
    if platform.system() == "Darwin":
        commands += [["sw_vers"]]
        commands += [["sysctl", "-n", key] for key in (
            "machdep.cpu.brand_string", "hw.model", "hw.physicalcpu", "hw.logicalcpu",
            "hw.memsize", "hw.cachelinesize", "hw.l1icachesize", "hw.l1dcachesize",
            "hw.l2cachesize", "hw.l3cachesize", "hw.perflevel0.physicalcpu",
            "hw.perflevel0.logicalcpu", "hw.perflevel0.l2cachesize",
            "hw.perflevel1.physicalcpu", "hw.perflevel1.logicalcpu",
            "hw.perflevel1.l2cachesize", "kern.hv_vmm_present")]
        commands += [["pmset", "-g", "custom"], ["pmset", "-g", "batt"],
                     ["xcode-select", "-p"], ["xcrun", "xctrace", "list", "templates"]]
    elif platform.system() == "Linux":
        commands += [["uname", "-srvmo"], ["lscpu"], ["free", "-b"],
                     ["systemd-detect-virt"], ["cat", "/proc/sys/kernel/perf_event_paranoid"]]
    return {
        "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(), "architecture": platform.machine(),
        "python": platform.python_version(),
        "tools": {name: shutil.which(name) for name in (
            "clang++", "g++", "cmake", "make", "ninja", "python3", "perf", "sample", "xctrace")},
        "observations": [command(args) for args in commands],
        "limits": ["CPU affinity and background load are uncontrolled.",
                   "No machine-wide settings changed.",
                   "Counter availability is not established by executable presence."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(inventory(), indent=2) + "\n")
