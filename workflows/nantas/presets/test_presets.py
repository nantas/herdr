import importlib.util
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
import json
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).with_name('herdr-project.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
PRESET = {'session': 'work', 'cwd': '/project', 'agent': 'codex', 'args': []}


class PresetTests(unittest.TestCase):
    def test_api_decodes_utf8_with_non_utf8_system_locale(self):
        run = subprocess.run
        payload = json.dumps({'result': {'title': '测试工作区'}}, ensure_ascii=False)

        def emit_response(command, **kwargs):
            return run([sys.executable, '-c',
                        'import sys; sys.stdout.buffer.write(bytes.fromhex(sys.argv[1]))',
                        payload.encode('utf-8').hex()], **kwargs)

        with patch.object(launcher.subprocess, 'run', side_effect=emit_response), \
                patch.object(subprocess, '_text_encoding', return_value='gbk'):
            self.assertEqual(launcher.api(['--session', 'work'], 'pane', 'list'),
                             {'title': '测试工作区'})

    def test_picker_child_outputs_utf8_with_non_utf8_parent_locale(self):
        with tempfile.TemporaryDirectory() as directory:
            child = Path(directory) / 'launcher.py'
            child.write_text("import json\nprint(json.dumps({'status': '测试🚀'}, ensure_ascii=False))\n",
                             encoding='utf-8')
            with patch.object(launcher, '__file__', str(child)), \
                    patch.dict(launcher.os.environ, {'PYTHONIOENCODING': 'gbk'}), \
                    patch.object(subprocess, '_text_encoding', return_value='gbk'):
                self.assertIn('测试🚀', launcher.launch_selected('project', PRESET))

    def test_paths_are_validated_for_execution_node(self):
        for cwd in ('/remote/project', r'D:\Projects\art'):
            launcher.validate('project', {**PRESET, 'cwd': cwd})
        for cwd in ('relative', 'D:relative'):
            with self.assertRaises(ValueError):
                launcher.validate('project', {**PRESET, 'cwd': cwd})

    def test_lock_excludes_another_process_and_releases(self):
        script = '''import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('launcher', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.launch_lock(pathlib.Path(sys.argv[2])):
    pass
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'launch.lock'
            command = [sys.executable, '-c', script, launcher.__file__, str(path)]
            with launcher.launch_lock(path):
                self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def pane(self, cwd='/project', terminal='t1', agent='codex'):
        return {'pane_id': 'w1:p1', 'terminal_id': terminal, 'foreground_cwd': cwd,
                'cwd': '/project', 'agent': agent}

    def test_launcher_environment_removes_no_color_without_mutating_parent(self):
        with patch.dict(launcher.os.environ, {'NO_COLOR': '1', 'COLORTERM': 'truecolor'}):
            env = launcher.clean_env()
            self.assertNotIn('NO_COLOR', env)
            self.assertEqual(env['COLORTERM'], 'truecolor')
            self.assertEqual(launcher.os.environ['NO_COLOR'], '1')

    def test_actual_directory_wins_over_original_directory(self):
        pane = self.pane(cwd='/other-project')
        self.assertIsNone(launcher.choose([pane], PRESET, {'terminal_id': 't1'}))

    def test_reuse_and_ambiguity(self):
        first, second = self.pane(), self.pane(terminal='t2')
        self.assertIs(launcher.choose([first], PRESET, {}), first)
        with self.assertRaises(RuntimeError):
            launcher.choose([first, second], PRESET, {})
        self.assertIs(launcher.choose([first, second], PRESET, {'terminal_id': 't2'}), second)
        second['focused'] = True
        self.assertIs(launcher.choose([first, second], PRESET, {}), second)

    def test_other_agent_in_owned_pane_is_not_replaced(self):
        with self.assertRaises(RuntimeError):
            launcher.choose([self.pane(agent='claude')], PRESET, {'terminal_id': 't1'})

    def test_repeated_launch_starts_only_once(self):
        panes, calls, state = [], [], {}

        def call(*args):
            calls.append(args[:2])
            if args[:2] == ('pane', 'list'):
                return {'panes': panes}
            if args[:2] == ('workspace', 'create'):
                self.assertEqual(args[args.index('--env') + 1], 'NO_COLOR=')
                panes.append(self.pane(agent=None))
                return {'root_pane': panes[0]}
            if args[:2] == ('agent', 'start'):
                panes[0]['agent'] = 'codex'
                return {'agent': panes[0]}
            if args[:2] == ('agent', 'focus'):
                return {}
            self.fail(str(args))

        first = launcher.ensure('project', PRESET, state, lambda: None, call)
        second = launcher.ensure('project', PRESET, state, lambda: None, call)
        self.assertEqual(first['status'], 'started')
        self.assertEqual(second['status'], 'reused')
        self.assertEqual(calls.count(('workspace', 'create')), 1)
        self.assertEqual(calls.count(('agent', 'start')), 1)

    def test_failed_start_keeps_identity_without_creating_again(self):
        pane, state, calls = self.pane(agent=None), {}, []

        def call(*args):
            calls.append(args[:2])
            if args[:2] == ('pane', 'list'):
                return {'panes': [] if not state else [pane]}
            if args[:2] == ('workspace', 'create'):
                return {'root_pane': pane}
            raise launcher.ApiError('agent_start_timeout', 'test timeout')

        for _ in range(2):
            with self.assertRaises(launcher.ApiError):
                launcher.ensure('project', PRESET, state, lambda: None, call)
        self.assertEqual(calls.count(('workspace', 'create')), 1)

    def test_validation_rejects_ambiguous_target(self):
        launcher.validate('project', PRESET)
        with self.assertRaises(ValueError):
            launcher.validate('project', {**PRESET, 'machine': 'remote'})
        with self.assertRaises(ValueError):
            launcher.validate('project', {**PRESET, 'cwd': 'relative'})


if __name__ == '__main__':
    unittest.main()
