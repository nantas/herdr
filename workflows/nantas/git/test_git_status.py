import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('viewer', Path(__file__).with_name('herdr-git-status.py'))
viewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewer)


class GitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'main'
        self.root.mkdir()
        self.git('init', '-q')
        for name in ('staged.txt', 'both.txt', 'unstaged.txt', 'old\tname.txt'):
            (self.root / name).write_text('original\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                 'commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True).stdout

    def test_all_states_rename_and_special_names_without_index_writes(self):
        for name in ('staged.txt', 'both.txt', 'unstaged.txt'):
            (self.root / name).write_text('changed\n')
        self.git('add', '--', 'staged.txt', 'both.txt')
        (self.root / 'both.txt').write_text('changed again\n')
        self.git('mv', '--', 'old\tname.txt', 'new\nname.txt')
        special = '空 格\tline\n"quote".txt'
        (self.root / special).write_text('untracked')
        (self.root / '-leading-dash').write_text('untracked')
        index = (self.root / '.git/index').read_bytes()
        root, rows = viewer.read_status(str(self.root))
        self.assertEqual(Path(root), self.root.resolve())
        self.assertIn(('M ', 'staged.txt', None), rows)
        self.assertIn((' M', 'unstaged.txt', None), rows)
        self.assertIn(('MM', 'both.txt', None), rows)
        self.assertIn(('R ', 'new\nname.txt', 'old\tname.txt'), rows)
        self.assertIn(('??', special, None), rows)
        self.assertIn(('??', '-leading-dash', None), rows)
        self.assertEqual(index, (self.root / '.git/index').read_bytes())
        rendered = viewer.format_row(('??', special, None))
        self.assertNotIn('\n', rendered)
        self.assertNotIn('\t', rendered)
        self.assertIn('空 格', rendered)

    def test_linked_worktree_from_subdirectory_ignores_git_overrides(self):
        worktree = Path(self.temp.name) / 'linked'
        self.git('worktree', 'add', '--detach', str(worktree), 'HEAD')
        (worktree / 'nested').mkdir()
        (worktree / 'only-linked').write_text('new')
        with patch.dict(os.environ, {'GIT_DIR': str(self.root / '.git'),
                                    'GIT_WORK_TREE': str(self.root)}):
            root, rows = viewer.read_status(str(worktree / 'nested'))
        self.assertEqual(Path(root), worktree.resolve())
        self.assertEqual(rows, [('??', 'only-linked', None)])

    def test_clean_non_git_and_missing_directory(self):
        self.assertEqual(viewer.read_status(str(self.root))[1], [])
        with self.assertRaisesRegex(RuntimeError, 'not a git repository'):
            viewer.read_status(self.temp.name)
        with self.assertRaises(RuntimeError):
            viewer.read_status(str(self.root / 'missing'))

    def test_malformed_records_and_undecodable_filename(self):
        for raw in (b'?? missing terminator', b'R  new\0', b'x\0'):
            with self.assertRaises(ValueError):
                viewer.parse_status(raw)
        row = viewer.parse_status(b'?? bad\xff\0')[0]
        viewer.format_row(row).encode('utf-8')

    def test_actual_directory_wins_and_missing_actual_directory_never_falls_back(self):
        pane = {'cwd': '/wrong', 'foreground_cwd': str(self.root)}
        result = subprocess.CompletedProcess([], 0, json.dumps({'result': {'pane': pane}}), '')
        with patch.dict(os.environ, {'HERDR_ACTIVE_PANE_ID': 'w1:p1', 'HERDR_SOCKET_PATH': '/test.sock'}), \
                patch.object(viewer.subprocess, 'run', return_value=result):
            self.assertEqual(viewer.active_directory(), str(self.root))
            for value in ({'cwd': str(self.root)}, {'foreground_cwd': '/unavailable-node-path'}):
                result.stdout = json.dumps({'result': {'pane': value}})
                with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                    viewer.active_directory()
        with patch.dict(os.environ, {}, clear=True), patch.object(viewer.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                viewer.active_directory()
            run.assert_not_called()


class Screen:
    def __init__(self, keys):
        self.keys = iter(keys)
        self.frames = []
    def getmaxyx(self):
        return 12, 50
    def erase(self):
        self.frames.append([])
    def addnstr(self, row, col, text, width):
        self.frames[-1].append(text[:width])
    def refresh(self):
        pass
    def timeout(self, value):
        pass
    def getch(self):
        return next(self.keys)


class ViewTests(unittest.TestCase):
    def test_raw_mouse_wheel_and_navigation_sequences(self):
        for sequence, expected in [('[<65;40;10M', 'wheel-down'), ('[<64;40;10M', 'wheel-up'),
                                   ('[B', viewer.curses.KEY_DOWN), ('[6~', viewer.curses.KEY_NPAGE)]:
            self.assertEqual(viewer.read_key(Screen([27, *map(ord, sequence)])), expected)
        self.assertEqual(viewer.read_key(Screen([27, -1])), 27)

    def test_mouse_keyboard_refresh_and_close(self):
        screen = Screen(['wheel-down', viewer.curses.KEY_END,
                         viewer.curses.KEY_HOME, ord('r'), ord('q')])
        rows = [('??', f'file-{i:02}', None) for i in range(30)]
        with patch.object(viewer.curses, 'curs_set'), patch.object(viewer.curses, 'mousemask'), \
                patch.object(viewer, 'active_directory', return_value='/repo') as cwd, \
                patch.object(viewer, 'read_status', return_value=('/repo', rows)) as read:
            viewer.view(screen)
        self.assertTrue(any('4-9/30' in line for line in screen.frames[1]))
        self.assertTrue(any('25-30/30' in line for line in screen.frames[2]))
        self.assertEqual(cwd.call_count, 2)
        self.assertEqual(read.call_count, 2)

    def test_refresh_failure_clears_stale_results_and_horizontal_scroll(self):
        screen = Screen([viewer.curses.KEY_RIGHT, ord('r'), ord('q')])
        with patch.object(viewer.curses, 'curs_set'), patch.object(viewer.curses, 'mousemask'), \
                patch.object(viewer, 'active_directory', return_value='/repo'), \
                patch.object(viewer, 'read_status', side_effect=[('/repo', [('??', 'x' * 100, None)]),
                                                               RuntimeError('query failed')]):
            viewer.view(screen)
        self.assertTrue(any('x' * 40 in line for line in screen.frames[1]))
        self.assertTrue(any('query failed' in line for line in screen.frames[2]))
        self.assertFalse(any('x' * 40 in line for line in screen.frames[2]))


if __name__ == '__main__':
    unittest.main()
