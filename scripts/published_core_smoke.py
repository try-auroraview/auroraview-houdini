"""Check an installed adapter against a hash-bound published Core wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import sysconfig
import unittest
import zipfile
from email.parser import BytesParser
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    subprocess.run(command, check=True, timeout=180, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-wheel", required=True, type=Path)
    parser.add_argument("--core-sha256", required=True)
    parser.add_argument("--typing-wheel", type=Path)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    core_wheel = args.core_wheel.resolve()
    assert digest(core_wheel) == args.core_sha256
    (candidate,) = args.dist.resolve().glob("*.whl")
    with zipfile.ZipFile(core_wheel) as archive:
        metadata = BytesParser().parsebytes(
            archive.read(
                next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            )
        )
        assert metadata["Name"] == "auroraview"
        native_members = [name for name in archive.namelist() if name.endswith(".pyd")]
        assert len(native_members) == 1
        expected_native = hashlib.sha256(archive.read(native_members[0])).hexdigest()
    if not args.inside:
        environment = root / (".published-env-py%d%d" % sys.version_info[:2])
        if not environment.exists():
            run(
                [
                    "vx",
                    "--no-auto-install",
                    "--cache-mode",
                    "offline",
                    "uv@0.12.7",
                    "venv",
                    "--python",
                    sys.executable,
                    str(environment),
                ]
            )
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        uv = [
            "vx",
            "--no-auto-install",
            "--cache-mode",
            "offline",
            "uv@0.12.7",
            "pip",
            "install",
            "--python",
            str(python),
            "--offline",
            "--no-deps",
            "--no-index",
        ]
        if sys.version_info < (3, 8):
            assert args.typing_wheel is not None
            run(uv + [str(args.typing_wheel.resolve())])
        run(uv + ["--reinstall", str(core_wheel), str(candidate)])
        env = os.environ.copy()
        env.update(
            {"PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1", "AURORAVIEW_DISABLE_WARMUP": "1"}
        )
        command = [
            str(python),
            str(Path(__file__).resolve()),
            "--inside",
            "--core-wheel",
            str(core_wheel),
            "--core-sha256",
            args.core_sha256,
            "--dist",
            str(args.dist.resolve()),
        ]
        run(command, env=env)
        return
    os.environ["AURORAVIEW_DISABLE_WARMUP"] = "1"
    sys.dont_write_bytecode = True
    src = (root / "src").resolve()
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != src]
    import auroraview
    import auroraview._core as native

    import auroraview_houdini

    site = Path(sysconfig.get_path("purelib")).resolve()
    assert Path(auroraview.__file__).resolve() == site / "auroraview/__init__.py"
    assert Path(auroraview_houdini.__file__).resolve() == site / "auroraview_houdini/__init__.py"
    assert Path(native.__file__).resolve().parent == site / "auroraview"
    assert digest(Path(native.__file__)) == expected_native
    with zipfile.ZipFile(candidate) as archive:
        for path in (site / "auroraview_houdini").glob("*.py"):
            assert path.read_bytes() == archive.read("auroraview_houdini/" + path.name)
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    accepted = result.wasSuccessful() and result.testsRun > 0 and not result.skipped
    record = {
        "accepted": accepted,
        "python": sys.version.split()[0],
        "tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "core_version": metadata["Version"],
        "core_wheel": {"file": core_wheel.name, "sha256": digest(core_wheel)},
        "candidate_wheel": {"file": candidate.name, "sha256": digest(candidate)},
        "native_sha256": expected_native,
        "module_paths": {
            "core": str(auroraview.__file__),
            "native": str(native.__file__),
            "candidate": str(auroraview_houdini.__file__),
        },
        "source_core_injection": False,
        "real_houdini": False,
        "native_webview_created": False,
        "native_bridge_acceptance": False,
    }
    (root / "evidence").mkdir(exist_ok=True)
    report = root / "evidence" / ("published-core-py%d%d.json" % sys.version_info[:2])
    report.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("RESULT_JSON=" + json.dumps(record, sort_keys=True))
    if not accepted:
        sys.exit(1)


if __name__ == "__main__":
    main()
