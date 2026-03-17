#!/usr/bin/env python
# -*- coding: utf-8 -*-

# readers.py by:
#    Agustin Zubiaga <aguz@sugarlabs.org>
#    Walter Bender <walter@sugarlabs.org>

# Copyright (C) 2019 Hrishi Patel
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import glob
import statvfs

from gettext import gettext as _

from sugar3 import env
from sugar3 import profile
from sugar3.datastore import datastore


class FreeSpaceReader():
    """Reader for Free Space
    Measure free space on disk.
    """

    def __init__(self):
        """Import chart data from file."""

        space = self._get_space()
        self._reader = ((_('Free space'), space[0]),
                        (_('Used space'), space[1]))
        self.xlabel = ""
        self.ylabel = ""

    def get_chart_data(self):
        """Return data suitable for pyCHA."""

        chart_data = []

        for row in self._reader:
            label, value = row[0], row[1]

            if label == "XLabel":
                self.xlabel = value

            elif label == "YLabel":
                self.ylabel = value

            else:
                chart_data.append((label, float(value)))

        return chart_data

    def _get_space(self):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        free_space = self._get_MBs(free_space)
        total_space = self._get_MBs(total_space)
        used_space = total_space - free_space

        return free_space, used_space, total_space

    def _get_MBs(self, space):
        space = space / (1024 * 1024)

        return space

    def _get_GBs(self, space):
        space = space / 1024

        return space

    def get_labels_name(self):
        """Return the h_label and y_label names."""

        return self.xlabel, self.ylabel


class TurtleReader():
    """Reader for Journal activity

    Import chart data from journal activity analysis
    """

    TACAT = {'clean':'forward', 'forward':'forward', 'back':'forward',
         'left':'forward', 'right':'forward', 'arc': 'arc',
         'xcor': 'coord', 'ycor': 'coord', 'heading': 'coord',
         'setxy2': 'setxy', 'seth': 'setxy', 'penup': 'pen', 'pendown': 'pen',
         'setpensize': 'pen', 'setcolor': 'pen', 'pensize': 'pen',
         'color': 'pen', 'setshade': 'pen', 'setgray': 'pen', 'shade': 'pen',
         'gray': 'pen', 'fillscreen': 'pen', 'startfill': 'fill',
         'stopfill': 'fill', 'plus2': 'number', 'minus2': 'number',
         'product2': 'number', 'division2': 'number', 'remainder2': 'number',
         'sqrt': 'number', 'identity2': 'number', 'and2': 'boolean',
         'or2': 'boolean', 'not': 'boolean', 'greater2': 'boolean',
         'less2': 'boolean', 'equal2': 'boolean', 'random': 'random',
         'repeat': 'repeat', 'forever': 'repeat', 'if': 'ifthen',
         'ifelse': 'ifthen', 'while': 'ifthen', 'until': 'ifthen',
         'hat': 'action', 'stack': 'action', 'storein': 'box', 'box': 'box',
         'luminance': 'sensor', 'mousex': 'sensor', 'mousey': 'sensor',
         'mousebutton2': 'sensor', 'keyboard': 'sensor', 'kbinput': 'sensor',
         'readpixel': 'sensor', 'see': 'sensor', 'time': 'sensor',
         'sound': 'sensor', 'volume': 'sensor', 'pitch': 'sensor',
         'resistance': 'sensor', 'voltage': 'sensor', 'video': 'media',
         'wait': 'media', 'camera': 'media', 'journal': 'media',
         'audio': 'media', 'show': 'media', 'setscale': 'media',
         'savepix': 'media', 'savesvg': 'media', 'mediawait': 'media',
         'mediapause': 'media', 'mediastop': 'media', 'mediaplay': 'media',
         'speak': 'media', 'sinewave': 'media', 'description': 'media',
         'push':'extras', 'pop':'extras', 'printheap':'extras',
         'clearheap':'extras', 'isheapempty2':'extras', 'chr':'extras',
         'int':'extras', 'myfunction': 'python', 'userdefined': 'python',
         'loadblock': 'python', 'loadpalette': 'python'}
    TAPAL = {'forward': 'turtlep', 'arc': 'turtlep', 'coord': 'turtlep',
         'setxy': 'turtlep', 'pen': 'penp', 'fill': 'penp', 'number': 'numberp',
         'random': 'numberp', 'boolean': 'numberp', 'repeat': 'flowp',
         'ifthen': 'flowp', 'action': 'boxp', 'box': 'boxp',
         'sensor': 'sensorp', 'media': 'mediap', 'extras': 'extrasp',
         'python': 'extrasp'}
    TASCORE = {'forward': 3, 'arc': 3, 'setxy': 2.5, 'coord': 4, 'turtlep': 5,
           'pen': 2.5, 'fill': 2.5, 'penp': 5,
           'number': 2.5, 'boolean': 2.5, 'random': 2.5, 'numberp': 0,
           'repeat': 2.5, 'ifthen': 7.5, 'flowp': 10,
           'box': 7.5, 'action': 7.5, 'boxp': 0,
           'media': 5, 'mediap': 0,
           'python': 5, 'extras': 5, 'extrasp': 0,
           'sensor': 5, 'sensorp': 0}
    PALS = ['turtlep', 'penp', 'numberp', 'flowp', 'boxp', 'sensorp', 'mediap',
            'extrasp']
    PALNAMES = [_('turtle'), _('pen'), _('number'), _('flow'), _('box'),
                _('sensor'), _('media'), _('extras')]

    def hasturtleblocks(self, path):
        ''' Parse turtle block data and generate score based on rubric '''

        fd = open(path)
        blocks = []
        # block name is second token in each line
        for line in fd:
            tokens = line.split(',')
            if len(tokens) > 1:
                token = tokens[1].strip('" [')
                blocks.append(token)

        score = []
        for i in range(len(self.PALS)):
            score.append([self.PALNAMES[i], 0])
        cats = []
        pals = []

        for b in blocks:
            if b in self.TACAT:
                if not self.TACAT[b] in cats:
                    cats.append(self.TACAT[b])
        for c in cats:
            if c in self.TAPAL:
                if not self.TAPAL[c] in pals:
                    pals.append(self.TAPAL[c])

        for c in cats:
            if c in self.TASCORE:
                score[self.PALS.index(self.TAPAL[c])][1] += self.TASCORE[c]

        for p in pals:
            if p in self.TASCORE:
                score[self.PALS.index(p)][1] += self.TASCORE[p]

        return score

    def __init__(self, file):

        self._reader = self.hasturtleblocks(file)
        self.xlabel = ""
        self.ylabel = ""

    def get_chart_data(self):
        """Return data suitable for pyCHA."""

        chart_data = []

        for row in self._reader:
            label, value = row[0], row[1]

            if label == "XLabel":
                self.xlabel = value

            elif label == "YLabel":
                self.ylabel = value

            else:
                chart_data.append((label, float(value)))

        return chart_data

    def get_labels_name(self):
        """Return the h_label and y_label names."""

        return self.xlabel, self.ylabel


MAX = 19
class ParseJournal():
    ''' Simple parser of datastore '''

    def __init__(self):
        self._dsdict = {}
        self._activity_name = []
        self._activity_count = []
       
        dsobjects, journal_entries = datastore.find({})
        for dobj in dsobjects:
            name = dobj.metadata['activity']
            activity_name = name.split('.')[-1]
            if not activity_name.isdigit():
                self._activity_name.append(activity_name)
                self._activity_count.append(1)

    def get_sorted(self):
        activity_tuples = []
        for i in range(len(self._activity_name)):
            activity_tuples.append((self._activity_name[i].replace('Activity',
                                                                   ''),
                                    self._activity_count[i]))
        sorted_tuples = sorted(activity_tuples, key=lambda x: x[1])
        activity_list = []
        count = 0
        length = len(sorted_tuples)
        for i in range(length):
            if i < MAX:
                activity_list.append([sorted_tuples[length - i - 1][0],
                                      sorted_tuples[length - i - 1][1]])
            else:
                count += sorted_tuples[length - i - 1][1]
        if count > 0:
            activity_list.append([_('Others'), count])
        return activity_list


class JournalReader():
    """Reader for Journal activity

    Import chart data from journal activity analysis
    """

    def __init__(self):

        self._reader = ParseJournal().get_sorted()
        self.xlabel = ""
        self.ylabel = ""

    def get_chart_data(self):
        """Return data suitable for pyCHA."""

        chart_data = []

        for row in self._reader:
            label, value = row[0], row[1]

            if label == "XLabel":
                self.xlabel = value

            elif label == "YLabel":
                self.ylabel = value

            else:
                chart_data.append((label, float(value)))

        return chart_data

    def get_labels_name(self):
        """Return the h_label and y_label names."""

        return self.xlabel, self.ylabel
