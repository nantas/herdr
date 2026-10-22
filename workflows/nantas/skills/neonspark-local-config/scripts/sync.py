#!/usr/bin/env python3
"""Push the four approved neonspark configs; never print their contents."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

SOURCE = Path('/Volumes/Shuttle/unity-projects/neonspark')
TARGET = Path('/home/nantas/data/projects/neonspark')
HOST = 'nantas@10.23.5.117'
FILES = (
    'Backend/CloudBase/.env.local.dev',
    'Backend/CloudBase/.env.local.prod',
    '.local/taptap-harden.json',
    '.agents/skills/fetch-codecks-bug/.local.env',
)
SCRIPT = '.agents/skills/neonspark-local-config/scripts/sync.py'
LIMIT = 1024 * 1024


def checked_path(root, relative):
    root = Path(root)
    if root.is_symlink() or root.resolve() != root.absolute() or not root.is_dir():
        raise ValueError('invalid project root')
    path = root
    for part in Path(relative).parts:
        if part in ('..', '/', ''):
            raise ValueError('invalid relative path')
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink rejected: ' + relative)
    if path.exists() and not path.is_file():
        raise ValueError('not a regular file: ' + relative)
    return path


def read_config(path):
    with path.open('rb') as stream:
        data = stream.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('config exceeds 1 MiB limit')
    return data


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.config-sync-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def receive(root, payload, apply=False):
    if not isinstance(payload, dict) or set(payload) != set(FILES):
        raise ValueError('payload must contain exactly the four approved files')
    incoming = {}
    for relative in FILES:
        data = base64.b64decode(payload[relative], validate=True)
        if len(data) > LIMIT:
            raise ValueError('config exceeds 1 MiB limit')
        incoming[relative] = data
    paths = {rel: checked_path(root, rel) for rel in FILES}
    if not apply:
        return {'files': {rel: ('unchanged' if p.exists() and read_config(p) == incoming[rel]
                               else 'replace' if p.exists() else 'create')
                          for rel, p in paths.items()}}

    local = root / '.local'
    if local.is_symlink():
        raise ValueError('symlink rejected: .local')
    local.mkdir(mode=0o700, exist_ok=True)
    lock_path = checked_path(root, '.local/neonspark-config-sync.lock')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Recheck after acquiring the writer lock, before backing up anything.
        paths = {rel: checked_path(root, rel) for rel in FILES}
        old = {rel: read_config(p) if p.exists() else None for rel, p in paths.items()}
        modes = {rel: stat.S_IMODE(p.stat().st_mode) if p.exists() else None
                 for rel, p in paths.items()}
        changed = [rel for rel in FILES if old[rel] != incoming[rel]]
        if not changed:
            return {'files': {rel: 'unchanged' for rel in FILES}, 'verified': True,
                    'backup': None}
        base = local / 'neonspark-config-backups'
        if base.is_symlink():
            raise ValueError('symlink rejected: backup directory')
        base.mkdir(mode=0o700, exist_ok=True)
        os.chmod(base, 0o700)
        backup = Path(tempfile.mkdtemp(prefix='batch-', dir=base))
        manifest = {rel: {'existed': old[rel] is not None, 'mode': modes[rel]}
                    for rel in changed}
        atomic_write(backup / 'manifest.json', json.dumps(manifest, indent=2).encode())
        for rel in changed:
            if old[rel] is not None:
                atomic_write(backup / 'original' / rel, old[rel])
        applied = []
        try:
            for rel in changed:
                p = checked_path(root, rel)
                current = read_config(p) if p.exists() else None
                if current != old[rel]:
                    raise ValueError('target changed during sync')
                atomic_write(p, incoming[rel])
                applied.append(rel)
            if any(read_config(paths[rel]) != incoming[rel] for rel in FILES):
                raise ValueError('verification failed')
        except Exception:
            failed = []
            for rel in reversed(applied):
                try:
                    p = checked_path(root, rel)
                    if read_config(p) != incoming[rel]:
                        raise ValueError('target changed during rollback')
                    if old[rel] is None:
                        p.unlink()
                    else:
                        atomic_write(p, old[rel], modes[rel])
                except Exception:
                    failed.append(rel)
            return {'error': 'sync failed', 'backup': str(backup),
                    'rollback_failed': failed, 'verified': False}
        return {'files': {rel: ('unchanged' if rel not in changed else
                               'replaced' if old[rel] is not None else 'created')
                          for rel in FILES}, 'backup': str(backup), 'verified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    group.add_argument('--receive-check', action='store_true', help=argparse.SUPPRESS)
    group.add_argument('--receive-apply', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.receive_check or args.receive_apply:
        if sys.platform != 'linux':
            raise ValueError('receiver must run on Linux')
        raw = sys.stdin.buffer.read(6 * LIMIT + 1)
        if len(raw) > 6 * LIMIT:
            raise ValueError('payload too large')
        result = receive(TARGET, json.loads(raw), args.receive_apply)
        print(json.dumps(result, ensure_ascii=False))
        return 1 if 'error' in result else 0
    if sys.platform != 'darwin':
        raise ValueError('run this workflow on the source Mac; no reverse connection')
    payload = {rel: base64.b64encode(read_config(checked_path(SOURCE, rel))).decode('ascii')
               for rel in FILES}
    command = shlex.join(['python3', str(TARGET / SCRIPT),
                         '--receive-apply' if args.apply else '--receive-check'])
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                             '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15',
                             '-o', 'ServerAliveCountMax=3', HOST, command],
                            input=json.dumps(payload).encode(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=120)
    if result.returncode:
        # Only relay structured status, never arbitrary shell startup output.
        try:
            report = json.loads(result.stdout)
            if isinstance(report, dict) and report.get('error') == 'sync failed':
                print(json.dumps(report))
        except (ValueError, UnicodeError):
            pass
        print('SSH/receiver failed; inspect target state before retrying.', file=sys.stderr)
        return 1
    report = json.loads(result.stdout)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        # Exception messages from parsers/OS calls can contain private input.
        print('Config sync stopped (' + type(error).__name__ + '); no contents logged.',
              file=sys.stderr)
        sys.exit(1)
