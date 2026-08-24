# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import types
import unittest

# gi is an apt-installed system package, not something `uvx pytest`'s
# own managed interpreter has -- skip rather than error when it isn't
# importable.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
except (ImportError, ValueError):
    raise unittest.SkipTest('gi is not available')

# jarabe isn't on sys.path outside a built/installed tree.
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# expandedentry reaches jarabe.config through the palettes import;
# it's generated at build time and absent on a bare checkout.
try:
    import jarabe.config  # noqa: E402,F401
except ImportError:
    _config_stub = types.ModuleType('jarabe.config')
    _config_stub.prefix = '/usr'
    _config_stub.data_path = '/usr/share/sugar'
    _config_stub.version = '0.999'
    sys.modules['jarabe.config'] = _config_stub

from gi.repository import GdkPixbuf  # noqa: E402

from jarabe.journal.expandedentry import _trim_letterbox  # noqa: E402


def _rgba(width, height, fill=0xffffffff):
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8,
                                  width, height)
    pixbuf.fill(fill)
    return pixbuf


class TestTrimLetterbox(unittest.TestCase):

    def test_transparent_bars_are_cut_like_grey_ones(self):
        pixbuf = _rgba(40, 30)
        # subpixbufs share the parent's memory, so filling them paints
        # the margins in place
        pixbuf.new_subpixbuf(0, 0, 40, 6).fill(0x00000000)
        pixbuf.new_subpixbuf(0, 24, 40, 6).fill(0x00000000)
        trimmed = _trim_letterbox(pixbuf)
        self.assertEqual((trimmed.get_width(), trimmed.get_height()),
                         (40, 18))

    def test_a_blank_too_small_to_frame_stays_whole(self):
        # the trim never eats past the middle third, so only a
        # one-pixel blank can collapse to nothing
        pixbuf = _rgba(1, 1, fill=0x00000000)
        self.assertIs(_trim_letterbox(pixbuf), pixbuf)

    def test_a_large_blank_keeps_its_middle_third(self):
        trimmed = _trim_letterbox(_rgba(30, 30, fill=0x00000000))
        self.assertEqual((trimmed.get_width(), trimmed.get_height()),
                         (10, 10))

    def test_a_preview_without_bars_is_untouched(self):
        pixbuf = _rgba(40, 30)
        trimmed = _trim_letterbox(pixbuf)
        self.assertEqual((trimmed.get_width(), trimmed.get_height()),
                         (40, 30))

    def test_none_passes_through(self):
        self.assertIsNone(_trim_letterbox(None))


if __name__ == '__main__':
    unittest.main()
