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

"""The paper design language, in one place.

Every surface the reflection feature draws - the entry page's desk, the
talk rail, Jo's own face, the moment card, the invite note - shares
this module as the single source of color and font values.

Two color families exist because two surfaces genuinely differ: the
entry page's desk (expandedentry, reflectionview, and momentcard's own
card) reads slightly warmer than the bench tones the invite note and
Jo's glyph wear (reflectiontrigger, joglyph). Names carry a _PAGE /
_PANEL suffix wherever the two disagree; where every surface already
used the same value, they share one name.
"""

from sugar3.graphics import style


def px(n):
    return style.zoom(n)


def pxf(n):
    return style.ZOOM_FACTOR * n


INK_PAGE = '#3A3226'
INK_SOFT_PAGE = '#8A8070'
PAPER_PAGE = '#FFFDF7'
RIM_PAGE = '#E7DECB'
RULE_PAGE = '#C9E0EE'

INK_PANEL = '#2B2B2B'
MOUNT_LINE = '#DDD8C9'
CHIP_LINE = '#DCDFE6'

CARD = '#FFFFFF'
EMBER = '#E8A33D'
INK_FAINT = '#B9B0A0'

# momentcard's own rim value - kept separate, not folded into RIM_PAGE.
RIM_MOMENT = '#E9E4D8'

KRAFT = '#E8DCC8'
KRAFT_DEEP = '#DFD0B6'
ART_BG = '#FCFBF7'
TAG_LINE = '#CBBC9E'
TAG_ADD = '#A79B82'

MARK_INK = '#C4BAA3'
MARGIN_RED = '#F0A8A0'

JO_DISC_FILL = '#EDEEF1'
JO_DISC_LINE = '#D5D6DA'

FONT_HAND = "'Patrick Hand', cursive"
FONT_ROUND = "'Quicksand', 'Sans Serif', sans-serif"
FONT_CLEAR = "'Andika', 'Sans Serif', sans-serif"

# Plain family name, for call sites that build a Pango.FontDescription
# string - Pango parses comma lists fine, but would take FONT_HAND's
# quotes and CSS generic 'cursive' literally as part of the name.
FONT_HAND_FAMILY = 'Patrick Hand'
