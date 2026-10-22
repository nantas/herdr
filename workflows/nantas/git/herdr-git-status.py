#!/usr/bin/env python3
"""Read-only Git changed-file popup for the active Herdr pane on this node."""
import curses
import json
import os
import re
from pathlib import Path
import subprocess
import sys


def active_directory():
    pane_id = os.environ.get('HERDR_ACTIVE_PANE_ID')
    if not pane_id or not os.environ.get('HERDR_SOCKET_PATH'):
        raise RuntimeError('No active pane. Open this tool with the Herdr Git popup shortcut.')
    result = subprocess.run([os.environ.get('HERDR_BIN_PATH', 'herdr'), 'pane', 'get', pane_id],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError('Cannot read active pane: ' + result.stderr.strip())
    pane = json.loads(result.stdout)['result']['pane']
    cwd = pane.get('foreground_cwd')
    if not cwd or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise RuntimeError('Active pane directory is unavailable on this node; no repository queried.')
    return cwd


def parse_status(raw):
    fields = raw.split(b'\0')
    if fields.pop() != b'':
        raise ValueError('Incomplete Git status output')
    rows = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4 or entry[2:3] != b' ':
            raise ValueError('Invalid Git status record')
        status = entry[:2].decode('ascii')
        path = os.fsdecode(entry[3:])
        original = None
        if 'R' in status or 'C' in status:
            if index >= len(fields):
                raise ValueError('Missing rename source')
            original = os.fsdecode(fields[index])
            index += 1
        rows.append((status, path, original))
    return rows


def read_status(cwd):
    env = os.environ.copy()
    # A pane's Git overrides must not redirect the explicitly selected worktree.
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'):
        env.pop(key, None)
    env['GIT_OPTIONAL_LOCKS'] = '0'
    def git(*args):
        result = subprocess.run(['git', '-C', cwd, *args], env=env,
                                capture_output=True, timeout=15)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace').strip() or 'Git query failed')
        return result.stdout
    root = os.fsdecode(git('rev-parse', '--show-toplevel').removesuffix(b'\n'))
    rows = parse_status(git('-c', 'status.renames=true', 'status', '--porcelain=v1', '-z',
                            '--untracked-files=all'))
    return root, rows


def quoted(path):
    return json.dumps(path, ensure_ascii=False).encode('utf-8', errors='backslashreplace').decode()


def format_row(row):
    status, path, original = row
    name = quoted(path)
    if original is not None:
        name = quoted(original) + ' -> ' + name
    return status + '  ' + name


def draw(screen, row, text):
    height, width = screen.getmaxyx()
    if row >= height or width < 2:
        return
    text = ''.join(char if char.isprintable() else ' ' for char in text)
    try:
        screen.addnstr(row, 0, text, width - 1)
    except curses.error:
        pass  # A resize can invalidate dimensions between these calls.


def read_key(screen):
    key = screen.getch()
    if key != 27:
        return key
    # macOS curses lacks button 5; decode SGR mouse and navigation keys directly.
    screen.timeout(40)
    sequence = ''
    try:
        for _ in range(32):
            value = screen.getch()
            if value < 0:
                return 27
            sequence += chr(value)
            if len(sequence) > 1 and (sequence[-1].isalpha() or sequence[-1] == '~'):
                break
    finally:
        screen.timeout(-1)
    mouse = re.fullmatch(r'\[<(\d+);\d+;\d+M', sequence)
    if mouse and int(mouse[1]) & 64:
        return 'wheel-down' if int(mouse[1]) & 1 else 'wheel-up'
    return {'[A': curses.KEY_UP, '[B': curses.KEY_DOWN,
            '[C': curses.KEY_RIGHT, '[D': curses.KEY_LEFT,
            '[5~': curses.KEY_PPAGE, '[6~': curses.KEY_NPAGE,
            '[H': curses.KEY_HOME, '[F': curses.KEY_END,
            'OH': curses.KEY_HOME, 'OF': curses.KEY_END,
            '[1~': curses.KEY_HOME, '[4~': curses.KEY_END}.get(sequence, -1)


def popup(screen):
    screen.keypad(False)
    sys.stdout.write('\x1b[?1000h\x1b[?1006h')
    sys.stdout.flush()
    try:
        view(screen)
    finally:
        sys.stdout.write('\x1b[?1000l\x1b[?1006l')
        sys.stdout.flush()


def view(screen):
    curses.curs_set(0)
    curses.set_escdelay(25)
    top = left = 0
    refresh = True
    root = ''
    lines = []
    while True:
        if refresh:
            try:
                root, rows = read_status(active_directory())
                lines = [format_row(row) for row in rows] or ['Clean worktree - no changed files.']
            except Exception as error:
                root = ''
                lines = ['Unable to read Git status:', str(error)]
            refresh = False
        height, width = screen.getmaxyx()
        page = max(1, height - 6)
        top = max(0, min(top, max(0, len(lines) - page)))
        left = max(0, min(left, max(0, max(map(len, lines), default=0) - max(1, width - 1))))
        screen.erase()
        draw(screen, 0, 'Git changes - ' + (quoted(root) if root else 'unavailable'))
        draw(screen, 1, 'Columns: 1=staged | 2=unstaged | blank=unchanged')
        draw(screen, 2, 'M=modified A=added D=deleted R=renamed ??=untracked')
        for row, line in enumerate(lines[top:top + page], 3):
            draw(screen, row, line[left:])
        draw(screen, max(0, height - 3), f'{top + 1}-{min(top + page, len(lines))}/{len(lines)}  Up/Down/PgUp/PgDn or wheel')
        draw(screen, max(0, height - 2), 'Left/Right: pan | Home/End: top/bottom')
        draw(screen, max(0, height - 1), 'r: refresh | Esc/q: close')
        screen.refresh()
        key = read_key(screen)
        if key in (27, ord('q'), 3):
            return
        if key == ord('r'):
            refresh = True
        elif key in (curses.KEY_UP, ord('k')):
            top -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            top += 1
        elif key == curses.KEY_PPAGE:
            top -= page
        elif key == curses.KEY_NPAGE:
            top += page
        elif key == curses.KEY_HOME:
            top = left = 0
        elif key == curses.KEY_END:
            top = len(lines)
        elif key == curses.KEY_LEFT:
            left -= 8
        elif key == curses.KEY_RIGHT:
            left += 8
        elif key == 'wheel-up':
            top -= 3
        elif key == 'wheel-down':
            top += 3



if __name__ == '__main__':
    curses.wrapper(popup)
