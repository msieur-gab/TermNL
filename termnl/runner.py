"""Runs the command the agent filled in, or pretends to.

A skill named in settings.md's "simulate:" line is never run: the reply says it was simulated and
shows what would have run. This keeps a development machine safe from "restart the board".
Every command runs with $HOME set to TermNL's home, so files land there."""
import os
import subprocess

# opening an app or a file starts a program that stays open: it is started, not waited for
DETACHED = ("setsid ", "xdg-open ")


def run(command, home, timeout=10):
    """→ {ran: True, code, out, err} (or ran False with err when it couldn't start)"""
    env = {**os.environ, "HOME": home}
    try:
        if command.startswith(DETACHED):
            subprocess.Popen(["bash", "-c", command], cwd=home, env=env, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ran": True, "code": 0, "out": "", "err": ""}
        r = subprocess.run(["bash", "-c", command], cwd=home, env=env, capture_output=True, text=True, timeout=timeout)
        return {"ran": True, "code": r.returncode, "out": r.stdout[-4000:], "err": r.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ran": True, "code": 124, "out": "", "err": "stopped after %d seconds" % timeout}
    except OSError as e:
        return {"ran": False, "code": 127, "out": "", "err": str(e)}
