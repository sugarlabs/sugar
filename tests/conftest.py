# Copyright (C) 2026 Sugar Labs
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Shared test configuration.

The runtime smoke gate spawns a GTK subprocess for every accepted
source, which would slow the whole suite and make unrelated pipeline
tests display-dependent; the critic round issues an extra
generate_text call that would confuse fake-provider call counters.
Keep both off by default; the tests that exercise them re-enable
them explicitly.
"""

import os

os.environ.setdefault('AOD_RUNTIME_CHECK', 'off')
os.environ.setdefault('AOD_CRITIC', 'off')
