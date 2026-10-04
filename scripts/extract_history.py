"""Reproduce the public path filter in a new independent clone."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--filter-repo", default="git-filter-repo")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    provenance = json.loads((Path(__file__).resolve().parents[1] / "PROVENANCE.json").read_text())
    if output.exists() or output == source or not output.parent.is_dir():
        parser.error("output must be a new directory below an existing parent")
    environment = os.environ.copy()
    environment["GIT_NO_LAZY_FETCH"] = "1"
    head = run(["git", "-C", str(source), "rev-parse", "HEAD"], env=environment).stdout.strip()
    if head != provenance["source_commit"]:
        parser.error("source HEAD differs from the declared public migration base")
    shallow = run(
        ["git", "-C", str(source), "rev-parse", "--is-shallow-repository"], env=environment
    )
    if shallow.stdout.strip() != "false":
        parser.error("a complete non-shallow source clone is required")
    promisor = subprocess.run(
        ["git", "-C", str(source), "config", "--local", "--get-regexp", r"remote\..*\.promisor"],
        capture_output=True,
        text=True,
    )
    if promisor.returncode == 0:
        parser.error("promisor/partial sources are unsuitable for history extraction")
    run(
        [
            "git",
            "clone",
            "--no-local",
            "--no-hardlinks",
            "--no-tags",
            "--single-branch",
            "--branch",
            "main",
            str(source),
            str(output),
        ],
        env=environment,
    )
    cloned_head = run(["git", "rev-parse", "HEAD"], cwd=output, env=environment).stdout.strip()
    if cloned_head != head:
        parser.error("cloned main differs from pinned source HEAD; filtering was not started")
    command = [args.filter_repo]
    paths = {
        "LICENSE": "LICENSE",
        "python/auroraview/utils/thread_dispatcher.py": "migration/legacy-thread-dispatcher.py",
        "python/auroraview/utils/thread_dispatcher/backends/houdini.py": (
            "src/auroraview_houdini/dispatcher.py"
        ),
        "python/auroraview/adapter/hosts.py": "src/auroraview_houdini/host.py",
        "docs/dcc/houdini.md": "docs/houdini.md",
        "docs/zh/dcc/houdini.md": "docs/zh/houdini.md",
    }
    for old, new in paths.items():
        command += ["--path", old]
        if old != new:
            command += ["--path-rename", old + ":" + new]
    run(command, cwd=output, env=environment)
    (output / "migration").mkdir(exist_ok=True)
    shutil.copyfile(output / ".git/filter-repo/commit-map", output / "migration/commit-map.txt")
    filtered = run(["git", "rev-parse", "HEAD"], cwd=output).stdout.strip()
    if filtered != provenance["filtered_head"]:
        parser.error("filtered HEAD differs from declared history; output is not accepted")
    print(
        json.dumps(
            {
                "source_commit": head,
                "filtered_head": filtered,
                "expected_filtered_head": provenance["filtered_head"],
                "scope": "History only; initialization/package edits are not replayed",
            }
        )
    )


if __name__ == "__main__":
    main()
