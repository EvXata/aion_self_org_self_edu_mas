#!/usr/bin/env python3
"""AION Populations — one-file setup / установка в один файл.

Send THIS file to anyone. They run it once:

    python3 aion-populations-setup.py

It will: create a private virtual env, install AION Populations from GitHub
(falling back to a tarball if git is missing), run the demo, and open the
dashboard in the browser. No prior setup, no manual cloning.

Отправьте ЭТОТ файл. Запуск:  python3 aion-populations-setup.py
Скрипт сам создаст окружение, поставит пакет, запустит демо и откроет дашборд.

Requires only Python 3.9+ and internet. Pure standard library.
"""
import os
import sys
import shutil
import subprocess
import tempfile
import webbrowser

REPO = "https://github.com/EvXata/aion_self_org_self_edu_mas"
TARBALL = "https://codeload.github.com/EvXata/aion_self_org_self_edu_mas/tar.gz/refs/heads/main"
VENV = os.path.expanduser("~/.aion-populations")
PORT = 8092


def _run(cmd, **kw):
    print("›", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, **kw)


def _venv_python(venv):
    sub = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    return os.path.join(venv, sub, exe)


def main():
    print("=" * 56)
    print("  AION Populations — setup")
    print("  self-organizing · self-educating agent populations")
    print("=" * 56)

    if sys.version_info < (3, 9):
        sys.exit(f"Needs Python 3.9+. You have {sys.version.split()[0]}.")

    # 1. private virtual env (avoids old-pip / externally-managed issues)
    if not os.path.exists(_venv_python(VENV)):
        print(f"\n[1/4] creating environment at {VENV}")
        _run([sys.executable, "-m", "venv", VENV])
    vpy = _venv_python(VENV)
    _run([vpy, "-m", "pip", "install", "-q", "--upgrade", "pip"])

    # 2. install the package — git first, tarball fallback (no git needed)
    print("\n[2/4] installing AION Populations from GitHub")
    ok = _run([vpy, "-m", "pip", "install", "-q",
               f"aion-populations @ git+{REPO}.git"]).returncode == 0
    if not ok:
        print("  git path unavailable — downloading source tarball instead…")
        import urllib.request
        import tarfile
        tmp = tempfile.mkdtemp()
        tgz = os.path.join(tmp, "src.tgz")
        urllib.request.urlretrieve(TARBALL, tgz)
        with tarfile.open(tgz) as t:
            t.extractall(tmp)
        roots = [os.path.join(tmp, d) for d in os.listdir(tmp)
                 if d.startswith("aion_self_org") and os.path.isdir(os.path.join(tmp, d))]
        if not roots or _run([vpy, "-m", "pip", "install", "-q", roots[0]]).returncode != 0:
            sys.exit(f"Install failed. Try manually:  {vpy} -m pip install {REPO}")
        shutil.rmtree(tmp, ignore_errors=True)

    # 3. demo (60-second proof — certifies mechanisms, FDR-controlled)
    print("\n[3/4] running the demo")
    if _run([vpy, "-m", "aionpop", "demo"]).returncode != 0:
        sys.exit("Demo failed to run.")

    # 4. deploy the Claude Code skill + open one-click feedback (auto-feedback via the agent)
    print("\n[4/4] deploying the Claude Code skill + feedback")
    _run([vpy, "-m", "aionpop", "claude-init"])
    _run([vpy, "-m", "aionpop", "feedback", "tried the demo", "--open"])

    print("\nDone ✓")
    print(f"  - Dashboard:       {vpy} -m aionpop dashboard")
    print('  - In Claude Code:  open this folder and say "use aion populations".')
    print("  - Feedback opened in your browser - one click to send it.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Re-run any time:  python3 aion-populations-setup.py")
