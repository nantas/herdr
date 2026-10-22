import base64
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('config_sync', Path(__file__).with_name('sync.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class ConfigSyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.data = {rel: ('new\r\n' + rel).encode() for rel in sync.FILES}
        self.payload = {rel: base64.b64encode(data).decode()
                        for rel, data in self.data.items()}

    def test_check_backup_create_replace_and_noop(self):
        existing = self.root / sync.FILES[0]
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b'old\x00bytes\r\n')
        preview = sync.receive(self.root, self.payload)
        self.assertEqual(preview['files'][sync.FILES[0]], 'replace')
        self.assertFalse((self.root / '.local').exists())
        report = sync.receive(self.root, self.payload, True)
        self.assertTrue(report['verified'])
        backup = Path(report['backup'])
        self.assertEqual((backup / 'original' / sync.FILES[0]).read_bytes(), b'old\x00bytes\r\n')
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertFalse(json.loads((backup / 'manifest.json').read_text())[sync.FILES[1]]['existed'])
        for rel in sync.FILES:
            self.assertEqual((self.root / rel).read_bytes(), self.data[rel])
            self.assertEqual(stat.S_IMODE((self.root / rel).stat().st_mode), 0o600)
        self.assertIsNone(sync.receive(self.root, self.payload, True)['backup'])

    def test_mid_write_failure_restores_old_bytes_and_mode(self):
        first = self.root / sync.FILES[0]
        first.parent.mkdir(parents=True)
        first.write_bytes(b'original')
        first.chmod(0o640)
        original = sync.atomic_write

        def fail_second(path, data, mode=0o600):
            if path == self.root / sync.FILES[1]:
                raise OSError('synthetic write failure')
            return original(path, data, mode)

        with patch.object(sync, 'atomic_write', side_effect=fail_second):
            result = sync.receive(self.root, self.payload, True)
        self.assertFalse(result['verified'])
        self.assertEqual(result['rollback_failed'], [])
        self.assertEqual(first.read_bytes(), b'original')
        self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o640)
        self.assertFalse((self.root / sync.FILES[1]).exists())

    def test_rollback_removes_new_file(self):
        original = sync.atomic_write

        def fail_second(path, data, mode=0o600):
            if path == self.root / sync.FILES[1]:
                raise OSError('synthetic write failure')
            return original(path, data, mode)

        with patch.object(sync, 'atomic_write', side_effect=fail_second):
            result = sync.receive(self.root, self.payload, True)
        self.assertEqual(result['rollback_failed'], [])
        self.assertFalse((self.root / sync.FILES[0]).exists())

    def test_symlink_parent_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'Backend').symlink_to(outside)
            with self.assertRaises(ValueError):
                sync.receive(self.root, self.payload, True)
            self.assertEqual(list(Path(outside).iterdir()), [])
            self.assertFalse((self.root / '.local').exists())

    def test_incomplete_or_bad_payload_is_rejected_before_writes(self):
        incomplete = dict(self.payload)
        del incomplete[sync.FILES[0]]
        bad = dict(self.payload)
        bad[sync.FILES[-1]] = '!invalid!'
        for payload in (incomplete, bad):
            with self.assertRaises(ValueError):
                sync.receive(self.root, payload, True)
            self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
