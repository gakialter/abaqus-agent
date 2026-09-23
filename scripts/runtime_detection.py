# -*- coding: utf-8 -*-
"""Discover the supported external Python and one unambiguous Abaqus launcher."""
import os
import re
import shutil
import subprocess
from pathlib import Path

ABAQUS_NAMES = ("abaqus", "abq2026", "abaqus2026")


def which(name):
    return shutil.which(name)


def _is_python_311(command):
    try:
        result = subprocess.run(list(command) + ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                                capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and result.stdout.strip() == "3.11"
    except (OSError, subprocess.TimeoutExpired):
        return False


def detect_python():
    """Only external Python 3.11 is supported for the release venv."""
    candidates = []
    if which("py"):
        candidates.append(["py", "-3.11"])
    python = which("python")
    if python:
        candidates.append([python])
    for command in candidates:
        if _is_python_311(command):
            return command
    return None


def validate_abaqus_cmd(value):
    if not isinstance(value, str):
        raise ValueError("ABAQUS_CMD must be a string")
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if not value or any(ch in value for ch in '"\r\n\x00%'):
        raise ValueError("ABAQUS_CMD is empty or contains unsafe quoting/expansion")
    path = Path(value)
    if path.is_absolute():
        if path.suffix.lower() not in (".bat", ".exe") or not path.is_file():
            raise ValueError("Abaqus path must be an existing .bat or .exe")
        return str(path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Abaqus command must be one command name without arguments")
    resolved = which(value)
    if not resolved:
        raise ValueError("Abaqus command is not on PATH: " + value)
    return value


def detect_abaqus():
    candidates = []
    for name in ABAQUS_NAMES:
        found = which(name)
        if found:
            candidates.append(Path(found))
    for root in (Path(r"C:\Program Files\SIMULIA\EstProducts"),
                 Path(r"D:\SIMULIA\EstProducts")):
        if root.is_dir():
            candidates.extend(root.glob("*/win_b64/code/bin/abq2026.bat"))
    unique = {os.path.normcase(os.path.abspath(str(path))): str(path) for path in candidates}
    if len(unique) > 1:
        raise ValueError("Multiple Abaqus launchers found; enter one explicit path: " +
                         ", ".join(sorted(unique.values())))
    return validate_abaqus_cmd(next(iter(unique.values()))) if unique else None
