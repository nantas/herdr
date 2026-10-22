"""Check that only interactive Herdr shells clear NO_COLOR."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class ColorTests(unittest.TestCase):
    def test_shell_scope(self):
        source = Path(__file__).with_name('interactive-colors.sh').resolve()
        for shell in ('zsh', 'bash'):
            executable = shutil.which(shell)
            if not executable:
                continue
            for interactive in (True, False):
                for herdr in ('1', '0'):
                    with self.subTest(shell=shell, interactive=interactive, herdr=herdr):
                        result = subprocess.run(
                            [executable, '-f' if shell == 'zsh' else '--norc',
                             '-ic' if interactive else '-c',
                             '. "$1"; printf "COLOR_RESULT=%s\\n" "${NO_COLOR-unset}"',
                             'color-test', str(source)],
                            env={**os.environ, 'HERDR_ENV': herdr, 'NO_COLOR': '1'},
                            capture_output=True, text=True, check=True)
                        expected = 'unset' if interactive and herdr == '1' else '1'
                        self.assertIn('COLOR_RESULT=' + expected, result.stdout)


if __name__ == '__main__':
    unittest.main()
