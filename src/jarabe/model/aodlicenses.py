# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class LicenseInfo:
    key: str
    label: str
    spdx: str
    description: str
    common_license_file: str = ''
    fallback_text: str = ''

    def get_text(self):
        if self.common_license_file:
            path = os.path.join('/usr/share/common-licenses',
                                self.common_license_file)
            try:
                with open(path, encoding='utf-8') as license_file:
                    return license_file.read()
            except OSError:
                pass
        return self.fallback_text


_MIT_TEXT = """MIT License

Copyright (c) 2026 Sugar Labs and activity contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

_BSD_TEXT = """BSD 3-Clause License

Copyright (c) 2026, Sugar Labs and activity contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED.
"""


def _fallback(spdx, url):
    return (
        '%s\n\n'
        'This activity is licensed under %s. The canonical license text is '
        'available at:\n%s\n'
    ) % (spdx, spdx, url)


LICENSES = {
    'mit': LicenseInfo(
        'mit', 'MIT', 'MIT', 'Short permissive license',
        fallback_text=_MIT_TEXT),
    'gplv3_plus': LicenseInfo(
        'gplv3_plus', 'GPLv3+', 'GPL-3.0-or-later',
        'Share-alike license used by many Sugar activities',
        common_license_file='GPL-3',
        fallback_text=_fallback(
            'GNU General Public License version 3 or later',
            'https://www.gnu.org/licenses/gpl-3.0.txt')),
    'apache_2': LicenseInfo(
        'apache_2', 'Apache', 'Apache-2.0',
        'Permissive license with an explicit patent grant',
        common_license_file='Apache-2.0',
        fallback_text=_fallback(
            'Apache License 2.0',
            'https://www.apache.org/licenses/LICENSE-2.0.txt')),
    'agplv3': LicenseInfo(
        'agplv3', 'AGPLv3', 'AGPL-3.0-or-later',
        'Network share-alike license',
        fallback_text=_fallback(
            'GNU Affero General Public License version 3 or later',
            'https://www.gnu.org/licenses/agpl-3.0.txt')),
    'lgplv3': LicenseInfo(
        'lgplv3', 'LGPLv3', 'LGPL-3.0-or-later',
        'Library-focused share-alike license',
        common_license_file='LGPL-3',
        fallback_text=_fallback(
            'GNU Lesser General Public License version 3 or later',
            'https://www.gnu.org/licenses/lgpl-3.0.txt')),
    'mpl_2': LicenseInfo(
        'mpl_2', 'MPL-2.0', 'MPL-2.0',
        'File-level share-alike license',
        common_license_file='MPL-2.0',
        fallback_text=_fallback(
            'Mozilla Public License 2.0',
            'https://www.mozilla.org/MPL/2.0/')),
    'bsd_3': LicenseInfo(
        'bsd_3', 'BSD-3', 'BSD-3-Clause',
        'Permissive license with attribution',
        fallback_text=_BSD_TEXT),
}


def get_license(value):
    if value in LICENSES:
        return LICENSES[value]

    for license_info in LICENSES.values():
        if value == license_info.spdx:
            return license_info

    raise ValueError('Unknown activity license: %s' % value)
