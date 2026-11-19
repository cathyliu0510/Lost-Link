"""Prepare/serve a NEW disposable run using the preserved instrumented service.

This launches the project, not a scripted client. Give a fresh agent only the
three coldstart input files. Existing recorded evidence is never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil

PROJECT = Path(__file__).resolve().parents[2]
RECORDED = Path(__file__).resolve().parent / "recorded"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "serve"])
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    folder = args.run_dir.expanduser().resolve()
    if folder == PROJECT or (PROJECT in folder.parents and ".hw9-runs" not in folder.relative_to(PROJECT).parts):
        parser.error("Use a disposable directory outside the source tree, or .hw9-runs/ inside it")

    os.environ["LOSTLINK_PROJECT_ROOT"] = str(PROJECT)
    if args.operation == "prepare":
        # Refuse reuse: credentials, database and evidence must belong to one run.
        folder.mkdir(parents=True, exist_ok=False, mode=0o700)
        (folder / "coldstart").mkdir(mode=0o700)
        shutil.copyfile(RECORDED / "experiment.py", folder / "experiment.py")
        shutil.copyfile(PROJECT / "docs/AGENT_GUIDE.md", folder / "coldstart/AGENT_GUIDE.md")
        # The frozen harness generates random credentials/IDs and a natural task.
        # Importing initializes its files; only 'serve' actually starts HTTP.
        runpy.run_path(str(folder / "experiment.py"), run_name="hw9_prepare")
        (folder / "private").chmod(0o700)
        for path in (folder / "private").iterdir():
            path.chmod(0o600)
        (folder / "coldstart/access.json").chmod(0o600)
        plan = json.loads((RECORDED / "plan.json").read_text())
        plan["context"] = "Prepared for a new documentation-only client session; no client run is claimed"
        plan["project_checkout_commit"] = None
        plan["documentation"] = "coldstart/AGENT_GUIDE.md"
        plan["source_integrity"] = "Use the current source hashes in pre_run_manifest.json"
        (folder / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        inputs = ["plan.json", "experiment.py", "coldstart/AGENT_GUIDE.md",
                  "coldstart/task.txt", "coldstart/access.json"]
        manifest = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "context": "New run; actual client independence/manual help must be recorded by the operator",
            "sha256": {name: digest(folder / name) for name in inputs},
            "project_source_sha256": {name: digest(PROJECT / name) for name in
                                      ["lostlink/server.py", "lostlink/matching.py"]},
        }
        (folder / "pre_run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Prepared {folder}. No client has been run.")
        print("Give the fresh client ONLY coldstart/AGENT_GUIDE.md, coldstart/access.json, and coldstart/task.txt.")
    else:
        required = [folder / name for name in ["experiment.py", "pre_run_manifest.json", "private/secrets.json"]]
        if not all(path.is_file() for path in required):
            parser.error("Run prepare first in a new directory")
        # This copy retains the original instrumentation byte-for-byte. Its
        # documented environment override selects this checkout portably.
        runpy.run_path(str(folder / "experiment.py"), run_name="__main__")


if __name__ == "__main__":
    main()
