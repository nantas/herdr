import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).with_name('herdr-project.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
PRESET = {'session': 'work', 'cwd': '/project', 'agent': 'codex'}


class Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.text = []

    def getmaxyx(self):
        return 24, 100

    def erase(self):
        pass

    def refresh(self):
        pass

    def addnstr(self, row, col, text, width, style):
        self.text.append(text)

    def getch(self):
        return next(self.keys)


class PickerTests(unittest.TestCase):
    def test_load_validates_existing_file_and_empty_or_invalid_presets(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(launcher, 'CONFIG', Path(directory)):
            path = Path(directory) / 'presets.json'
            for value in ({'project': PRESET}, {}, [], {'project': {**PRESET, 'cwd': 'relative'}}):
                path.write_text(json.dumps(value))
                if value == {'project': PRESET}:
                    self.assertEqual(launcher.load_presets(), value)
                else:
                    with self.assertRaises(ValueError):
                        launcher.load_presets()

    def run_picker(self, screen, presets=None):
        with patch.object(launcher.curses, 'curs_set'), patch.object(launcher.curses, 'mousemask'), \
                patch.object(launcher, 'load_presets', return_value=presets or {'project': PRESET}):
            launcher.pick_project(screen)

    def test_cancel_does_not_launch(self):
        with patch.object(launcher, 'launch_selected') as launch:
            self.run_picker(Screen([27]))
            launch.assert_not_called()

    def test_selection_calls_launcher_once_and_shows_node_and_directory(self):
        remote = {'machine': 'linux-work', 'cwd': '/remote', 'agent': 'codex'}
        screen = Screen([launcher.curses.KEY_DOWN, 10, 10])
        with patch.object(launcher, 'launch_selected', return_value='Select linux-work') as launch:
            self.run_picker(screen, {'project': PRESET, 'remote': remote})
            launch.assert_called_once_with('remote', remote)
        self.assertTrue(any('linux-work' in text for text in screen.text))
        self.assertIn('  /remote', screen.text)

    def test_mouse_click_selects_remote_row(self):
        remote = {'machine': 'linux-work', 'cwd': '/remote', 'agent': 'codex'}
        screen = Screen([launcher.curses.KEY_MOUSE, 10, 27])
        with patch.object(launcher.curses, 'getmouse', return_value=
                          (0, 2, 3, 0, launcher.curses.BUTTON1_CLICKED)), \
                patch.object(launcher, 'launch_selected', return_value='Select linux-work') as launch:
            self.run_picker(screen, {'project': PRESET, 'remote': remote})
            launch.assert_called_once_with('remote', remote)

    def test_local_success_exits_without_waiting_in_hidden_popup(self):
        with patch.object(launcher, 'launch_selected', return_value='started'), \
                patch.object(launcher, 'picker_message') as message:
            self.run_picker(Screen([10]))
            message.assert_not_called()

    def test_failure_stays_visible_until_dismissed(self):
        screen = Screen([10, 10])
        with patch.object(launcher, 'launch_selected', side_effect=RuntimeError('ambiguous agents')):
            self.run_picker(screen)
        self.assertTrue(any('ambiguous agents' in text for text in screen.text))

    def test_missing_config_has_visible_error(self):
        screen = Screen([27])
        with patch.object(launcher.curses, 'curs_set'), patch.object(launcher.curses, 'mousemask'), \
                patch.object(launcher, 'load_presets', side_effect=FileNotFoundError('presets.json')):
            launcher.pick_project(screen)
        self.assertTrue(any('presets.json' in text for text in screen.text))

    def test_launch_uses_same_script_no_attach_and_remote_hint(self):
        remote = {'machine': 'linux-work', 'cwd': '/remote', 'agent': 'codex'}
        result = subprocess.CompletedProcess([], 0, '{"status":"reused"}', '')
        with patch.object(launcher.subprocess, 'run', return_value=result) as run:
            message = launcher.launch_selected('remote', remote)
        self.assertEqual(run.call_args.args[0], [launcher.sys.executable,
                         str(Path(launcher.__file__).resolve()), 'remote', '--no-attach'])
        self.assertIn('Select linux-work', message)
        self.assertIn('reused', message)

    def test_failed_launch_and_timeout_are_not_retried(self):
        with patch.object(launcher.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 1, '', 'multiple agents')) as run:
            with self.assertRaisesRegex(RuntimeError, 'multiple agents'):
                launcher.launch_selected('project', PRESET)
            run.assert_called_once()
        with patch.object(launcher.subprocess, 'run', side_effect=subprocess.TimeoutExpired('launch', 180)):
            with self.assertRaises(subprocess.TimeoutExpired):
                launcher.launch_selected('project', PRESET)


if __name__ == '__main__':
    unittest.main()
