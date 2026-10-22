import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).with_name('herdr-project.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
PRESET = {'session': 'work', 'cwd': '/project', 'agent': 'codex', 'args': []}


class PresetTests(unittest.TestCase):
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
