# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Deterministic per-activity icons.

Every generated activity used to ship the same checkmark.  This module
renders a small Sugar-style SVG icon whose glyph follows the activity's
template/category and whose accent varies with the activity name, so
the home ring shows a distinct, colorizable icon per activity.  Icons
use Sugar's ``&stroke_color;``/``&fill_color;`` entities so they take
the learner's XO colors wherever Sugar recolors icons.
"""

import hashlib

_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
    '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [\n'
    '  <!ENTITY stroke_color "#282828">\n'
    '  <!ENTITY fill_color "#FFFFFF">\n'
    ']>\n'
)

_TEMPLATE = _HEADER + (
    '<svg xmlns="http://www.w3.org/2000/svg" width="55" height="55" '
    'viewBox="0 0 55 55">\n'
    '  <g transform="rotate(%(angle)d 27.5 27.5)">\n'
    '%(glyph)s'
    '  </g>\n'
    '  <circle cx="%(accent_x)d" cy="%(accent_y)d" r="3" '
    'fill="&stroke_color;"/>\n'
    '</svg>\n'
)

_S = 'stroke="&stroke_color;"'
_F = 'fill="&fill_color;"'
_SF = _S + ' ' + _F

_GLYPHS = {
    'quiz': (
        '    <rect x="12" y="10" width="31" height="35" rx="4" '
        + _SF + ' stroke-width="3"/>\n'
        '    <path d="M21 22 q0-6 6.5-6 q6.5 0 6.5 6 q0 5 -6.5 7 l0 3" '
        'fill="none" ' + _S + ' stroke-width="3.5" '
        'stroke-linecap="round"/>\n'
        '    <circle cx="27.5" cy="38" r="2.5" fill="&stroke_color;"/>\n'
    ),
    'grid': (
        '    <rect x="10" y="10" width="15" height="15" rx="2" '
        + _SF + ' stroke-width="3"/>\n'
        '    <rect x="30" y="10" width="15" height="15" rx="2" '
        + _SF + ' stroke-width="3"/>\n'
        '    <rect x="10" y="30" width="15" height="15" rx="2" '
        + _SF + ' stroke-width="3"/>\n'
        '    <rect x="30" y="30" width="15" height="15" rx="2" '
        'fill="&stroke_color;" ' + _S + ' stroke-width="3"/>\n'
    ),
    'canvas': (
        '    <path d="M12 40 Q20 20 30 28 Q42 38 44 14" fill="none" '
        + _S + ' stroke-width="4.5" stroke-linecap="round"/>\n'
        '    <circle cx="14" cy="42" r="5" ' + _SF
        + ' stroke-width="3"/>\n'
    ),
    'narrative': (
        '    <path d="M27.5 14 Q18 9 9 13 L9 41 Q18 37 27.5 42 '
        'Q37 37 46 41 L46 13 Q37 9 27.5 14 Z" '
        + _SF + ' stroke-width="3"/>\n'
        '    <path d="M27.5 14 L27.5 42" fill="none" '
        + _S + ' stroke-width="3"/>\n'
    ),
    'utility': (
        '    <circle cx="27.5" cy="27.5" r="10" ' + _SF
        + ' stroke-width="3.5"/>\n'
        '    <path d="M27.5 9 V17 M27.5 38 V46 M9 27.5 H17 '
        'M38 27.5 H46 M14.5 14.5 L20 20 M35 35 L40.5 40.5 '
        'M40.5 14.5 L35 20 M20 35 L14.5 40.5" fill="none" '
        + _S + ' stroke-width="3.5" stroke-linecap="round"/>\n'
    ),
    'chess': (
        '    <path d="M17 45 L38 45 L36 32 L40 20 L34 20 L34 24 '
        'L30 24 L30 20 L25 20 L25 24 L21 24 L21 20 L15 20 L19 32 Z" '
        + _SF + ' stroke-width="3" stroke-linejoin="round"/>\n'
    ),
    'carrom': (
        '    <circle cx="24" cy="31" r="12" ' + _SF
        + ' stroke-width="3.5"/>\n'
        '    <circle cx="38" cy="16" r="6" fill="&stroke_color;" '
        + _S + ' stroke-width="2"/>\n'
    ),
    'science': (
        '    <path d="M23 10 L23 24 L13 42 Q11 46 16 46 L39 46 '
        'Q44 46 42 42 L32 24 L32 10 Z" '
        + _SF + ' stroke-width="3" stroke-linejoin="round"/>\n'
        '    <path d="M20 10 L35 10" fill="none" ' + _S
        + ' stroke-width="3" stroke-linecap="round"/>\n'
        '    <circle cx="24" cy="38" r="2.5" fill="&stroke_color;"/>\n'
    ),
    'language': (
        '    <path d="M10 12 H45 V36 H26 L16 45 L18 36 H10 Z" '
        + _SF + ' stroke-width="3" stroke-linejoin="round"/>\n'
        '    <path d="M17 21 H38 M17 28 H32" fill="none" '
        + _S + ' stroke-width="3" stroke-linecap="round"/>\n'
    ),
    'games': (
        '    <circle cx="27.5" cy="27.5" r="18" ' + _SF
        + ' stroke-width="3.5"/>\n'
        '    <path d="M23 19 L37 27.5 L23 36 Z" '
        'fill="&stroke_color;"/>\n'
    ),
    'default': (
        '    <circle cx="27.5" cy="27.5" r="18" ' + _SF
        + ' stroke-width="3.5"/>\n'
        '    <path d="M18 28 L25 35 L38 20" fill="none" '
        + _S + ' stroke-width="4" stroke-linecap="round" '
        'stroke-linejoin="round"/>\n'
    ),
}

_CATEGORY_GLYPHS = {
    'science': 'science',
    'language': 'language',
    'games': 'games',
    'logic_math': 'grid',
    'tools_utils': 'utility',
    'creation': 'canvas',
}

_ACCENTS = ((46, 8), (46, 46), (8, 46), (8, 8))


def render_activity_icon(plan):
    """Return a Sugar-style SVG icon for this plan; never raises."""
    try:
        template = str(plan.get('template') or '')
        category = str(plan.get('category') or '')
        name = str(plan.get('name') or 'Activity')

        glyph_key = 'default'
        if template in _GLYPHS:
            glyph_key = template
        elif category in _CATEGORY_GLYPHS:
            glyph_key = _CATEGORY_GLYPHS[category]

        digest = int(
            hashlib.sha256(name.encode('utf-8')).hexdigest()[:8], 16)
        accent_x, accent_y = _ACCENTS[digest % len(_ACCENTS)]
        angle = (digest // 7) % 13 - 6  # -6..6 degrees

        return _TEMPLATE % {
            'glyph': _GLYPHS[glyph_key],
            'angle': angle,
            'accent_x': accent_x,
            'accent_y': accent_y,
        }
    except Exception:
        return _TEMPLATE % {
            'glyph': _GLYPHS['default'],
            'angle': 0,
            'accent_x': 46,
            'accent_y': 8,
        }
