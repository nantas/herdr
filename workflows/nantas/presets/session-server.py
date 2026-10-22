#!/usr/bin/env python3
"""Run a launchd-owned server in a separate POSIX session and wait for it."""
import signal
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: session-server.py PROGRAM [ARG ...]')
    child = subprocess.Popen(sys.argv[1:], start_new_session=True)

    def forward(signum, _frame):
        try:
            child.send_signal(signum)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    code = child.wait()
    raise SystemExit(code if code >= 0 else 128 - code)


if __name__ == '__main__':
    main()
