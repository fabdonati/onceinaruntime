"""Run one bounded replay configuration in fresh, sequential processes."""

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from capture_environment import command, inventory

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {"messages", "topics", "payload-bytes", "selected-topics", "selection-offset",
           "seed", "begin", "end", "hot-topic", "warmups", "repetitions"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_sources():
    listing = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             cwd=ROOT, capture_output=True, check=True).stdout
    paths = sorted(set(os.fsdecode(value) for value in listing.split(b"\0") if value))
    return {name: digest(ROOT / name) for name in paths
            if "/results/" not in name and (ROOT / name).is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path("build/release/bin/replay_bench"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--environment", type=Path,
                        help="Optional prior hardware inventory; a fresh observation is always captured")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    config = json.loads(args.config.read_text())
    if set(config) != OPTIONS or any(type(value) is not int or value < 0 for value in config.values()):
        parser.error("config must contain exactly the documented unsigned integer options")
    binary = args.binary.resolve()
    # Require and retain build metadata, avoiding accidental debug/sanitizer timing.
    build_dir = binary.parent.parent
    cache_path = build_dir / "CMakeCache.txt"
    cache = cache_path.read_text()
    if "CMAKE_BUILD_TYPE:STRING=Release\n" not in cache or "MEASURED_SANITIZERS:BOOL=OFF\n" not in cache:
        parser.error("smoke measurements require the release preset without sanitizers")
    source_hashes = public_sources()
    arguments = [str(binary)] + [part for key, value in sorted(config.items())
                                for part in ("--" + key, str(value))]
    environment = inventory() # Read-only; run before measured child processes.
    prior_inventory = json.loads(args.environment.read_text()) if args.environment else None
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 1, "preliminary": True, "status": "running",
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runner_command": [sys.executable, *sys.argv], "working_directory": str(Path.cwd()),
        "benchmark_command": arguments, "config": config, "runs_requested": args.runs,
        "git_revision": command(["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD"]),
        "git_status": command(["git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"]),
        "source_sha256": source_hashes, "binary_sha256": digest(binary),
        "environment": environment, "prior_hardware_inventory": prior_inventory,
        "method": {
            "clock": "std::chrono::steady_clock; nanoseconds; calibration not subtracted",
            "retrieval": "range bounds, output clear, record copy, index search/heap/allocation; pre-reserved output",
            "outside_timing": "generation, batch indexing, selection preparation, validation, hashing, serialization",
            "cache": "warm repeated queries; no cache flush or affinity; index and all output buffers resident",
            "order": "scan first on even repetitions, indexed first on odd repetitions",
            "units": "complete query duration; not per-message latency",
            "exclusions": "none; all successful observations retained; failure marks this manifest failed"}}
    manifest_path = args.output / "manifest.json"

    def save_manifest():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    save_manifest()
    # A new repository may have no HEAD. Retain the actual public sources as well as hashes.
    archive = args.output / "source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as snapshot:
        for name in source_hashes:
            snapshot.write(ROOT / name, arcname=name)
    manifest["source_archive_sha256"] = digest(archive)
    save_manifest()
    # Preserve exact generated build commands and effective cache flags beside the data.
    (args.output / "compile_commands.json").write_text((build_dir / "compile_commands.json").read_text())
    flags = [line for line in cache.splitlines() if line.startswith((
        "CMAKE_BUILD_TYPE:", "CMAKE_CXX_COMPILER:", "CMAKE_CXX_FLAGS", "CMAKE_EXE_LINKER_FLAGS",
        "CMAKE_OSX_ARCHITECTURES:", "CMAKE_OSX_DEPLOYMENT_TARGET:", "MEASURED_SANITIZERS:"))]
    (args.output / "build-flags.txt").write_text("\n".join(flags) + "\n")
    try:
        for run in range(args.runs):
            result = subprocess.run(arguments, capture_output=True, text=True)
            (args.output / f"run-{run:03d}.stderr.txt").write_text(result.stderr)
            result.check_returncode()
            data = json.loads(result.stdout)
            if data["parameters"] != config or len(data["observations"]) != 2 * config["repetitions"]:
                raise RuntimeError("unexpected benchmark configuration or observation count")
            (args.output / f"run-{run:03d}.json").write_text(result.stdout)
        if source_hashes != public_sources() or manifest["binary_sha256"] != digest(binary):
            raise RuntimeError("sources or executable changed during runs")
        manifest["status"] = "complete"
    except BaseException as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        raise
    finally:
        manifest["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save_manifest()
    print(f"Saved {args.runs} preliminary runs to {args.output}")


if __name__ == "__main__":
    main()
