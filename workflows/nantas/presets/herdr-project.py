#!/usr/bin/env python3
"""Open a fixed directory/agent preset without replacing existing work."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

CONFIG = Path.home() / '.config/herdr-project'


class ApiError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(code + ': ' + message)


def clean_env():
    env = os.environ.copy()
    for key in ('HERDR_SOCKET_PATH', 'HERDR_CLIENT_SOCKET_PATH', 'HERDR_SESSION',
                'HERDR_WORKSPACE_ID', 'HERDR_TAB_ID', 'HERDR_PANE_ID'):
        env.pop(key, None)
    return env


def api(prefix, *args):
    result = subprocess.run(['herdr', *prefix, *args], env=clean_env(),
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        try:
            error = json.loads(result.stderr)['error']
        except (ValueError, KeyError):
            raise RuntimeError(result.stderr.strip() or 'Herdr command failed')
        raise ApiError(error['code'], error.get('message', ''))
    return json.loads(result.stdout)['result']


def validate(name, preset):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,23}', name):
        raise ValueError('preset name must be 1–24 lowercase letters/digits/_/-')
    if not isinstance(preset, dict) or set(preset) - {'session', 'machine', 'cwd', 'agent', 'args'}:
        raise ValueError('unknown preset fields')
    if ('session' in preset) == ('machine' in preset):
        raise ValueError('specify exactly one session or saved machine')
    for key in ('cwd', 'agent', 'session' if 'session' in preset else 'machine'):
        value = preset.get(key)
        if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
            raise ValueError('invalid ' + key)
    if not Path(preset['cwd']).is_absolute():
        raise ValueError('cwd must be an absolute path on the execution node')
    if not isinstance(preset.get('args', []), list) or any(
        not isinstance(arg, str) or any(ord(c) < 32 for c in arg)
        for arg in preset.get('args', [])
    ):
        raise ValueError('args must be an array of command arguments')


def at_directory(pane, cwd):
    return (pane.get('foreground_cwd') or pane.get('cwd')) == cwd


def choose(panes, preset, previous):
    # A recorded terminal moved to another project is not the preset anymore.
    matching = [p for p in panes if at_directory(p, preset['cwd'])]
    recorded = next((p for p in matching if p['terminal_id'] == previous.get('terminal_id')), None)
    if recorded and recorded.get('agent') == preset['agent']:
        return recorded
    agents = [p for p in matching if p.get('agent') == preset['agent']]
    if len(agents) > 1:
        focused = [p for p in agents if p.get('focused')]
        if len(focused) == 1:
            return focused[0]
        raise RuntimeError('Multiple matching agents; choose the desired instance in Herdr first. '
                           'No new agent was started.')
    if agents:
        return agents[0]
    if recorded:
        if recorded.get('agent'):
            raise RuntimeError('The recorded pane is running another agent; leaving it untouched.')
        return recorded
    return None


def save_state(path, state):
    fd, name = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(state, stream, indent=2)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def ensure(name, preset, state, persist, call):
    previous = state.get(name, {})
    if previous.get('preset') != preset:
        previous = {}
    panes = call('pane', 'list')['panes']
    pane = choose(panes, preset, previous)
    created = False
    if pane is None:
        result = call('workspace', 'create', '--cwd', preset['cwd'], '--label', name, '--no-focus')
        pane = result['root_pane']
        created = True
    state[name] = {'terminal_id': pane['terminal_id'], 'pane_id': pane['pane_id'], 'preset': preset}
    persist()
    status = 'reused'
    if not pane.get('agent'):
        # Only retry the new shell's startup race; never retry ambiguous submissions.
        deadline = time.monotonic() + 5
        while True:
            try:
                result = call('agent', 'start', name + '-' + uuid.uuid4().hex[:6], '--kind', preset['agent'],
                              '--pane', pane['pane_id'], '--', *preset.get('args', []))
                status = 'started'
                break
            except ApiError as error:
                if created and error.code == 'agent_pane_busy' and time.monotonic() < deadline:
                    time.sleep(0.2)
                    continue
                if error.code == 'agent_not_ready':
                    status = 'needs-input'
                    break
                raise
    call('agent', 'focus', pane['pane_id'])
    return {'preset': name, 'status': status, 'pane_id': pane['pane_id'], 'cwd': preset['cwd']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preset', nargs='?')
    parser.add_argument('--no-attach', action='store_true', help='prepare/focus and print status only')
    args = parser.parse_args()
    presets = json.loads((CONFIG / 'presets.json').read_text())
    if not args.preset:
        for name, preset in presets.items():
            print(name + '  ' + preset.get('machine', 'local/' + preset.get('session', ''))
                  + '  ' + preset['cwd'] + '  ' + preset['agent'])
        return
    if args.preset not in presets:
        raise ValueError('unknown preset; run herdr-project to list presets')
    preset = presets[args.preset]
    validate(args.preset, preset)
    if not args.no_attach and not sys.stdin.isatty():
        raise ValueError('run in an interactive terminal or add --no-attach')
    if not args.no_attach and os.environ.get('HERDR_ENV') == '1':
        raise ValueError('inside Herdr use --no-attach, then select the workspace in the sidebar')
    prefix = ['--machine', preset['machine']] if 'machine' in preset else ['--session', preset['session']]
    attach = ['herdr', 'session', 'attach', preset.get('session', 'work')]
    if 'machine' in preset:
        catalog = subprocess.run(['herdr', 'machine', 'list', '--json'], env=clean_env(),
                                 capture_output=True, text=True, check=True, timeout=15)
        profiles = [p for p in json.loads(catalog.stdout) if p['enabled'] and
                    preset['machine'] in (p['id'], p['label'])]
        if len(profiles) != 1:
            raise ValueError('saved machine must resolve to one enabled profile')
        attach = ['herdr', '--remote', profiles[0]['target'], '--session', profiles[0]['session']]
    state_path = CONFIG / 'state.json'
    with (CONFIG / 'launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        try:
            result = ensure(args.preset, preset, state, lambda: save_state(state_path, state),
                            lambda *a: api(prefix, *a))
        except Exception:
            print('No running work was stopped. Inspect Herdr before retrying. '
                  'If the server is stopped, attach to its work session first.', file=sys.stderr)
            raise
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if not args.no_attach:
        os.execvpe('herdr', attach, clean_env())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
