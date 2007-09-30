import os

import gtk
import hippo
import gnomevfs
from louie import dispatcher

from sugar import env

class LogEntry(object):
    def __init__(self, text):
        self.text = text.strip()

class LogModel(list):
    def __init__(self, path):
        self.path = path
        self.position = 0

        self.read_lines()
        gnomevfs.monitor_add('file://' + self.path,
                             gnomevfs.MONITOR_FILE,
                             self._log_file_changed_cb)

    def read_lines(self):
        log_file = open(self.path, 'r')
        log_file.seek(self.position)

        for line in log_file.readlines():
            self.add_line(line)

        self.position = log_file.tell()
        log_file.close()

    def add_line(self, line):
        entry = LogEntry(line)
        self.append(entry)

        dispatcher.send('entry-added', self, entry)

    def _log_file_changed_cb(self, monitor_uri, info_uri, event):
        if event == gnomevfs.MONITOR_EVENT_CHANGED:
            self.read_lines()

class LogView(hippo.CanvasBox):
    def __init__(self, path):
        hippo.CanvasBox.__init__(self)

        self.model = LogModel(path)

        scrollbars = hippo.CanvasScrollbars()
        scrollbars.set_policy(hippo.ORIENTATION_HORIZONTAL,
                              hippo.SCROLLBAR_NEVER)
        widget = scrollbars.props.widget
        widget.props.vadjustment.connect('changed', self._vadj_changed_cb)
        self.append(scrollbars, hippo.PACK_EXPAND)

        self.box = hippo.CanvasBox(spacing=5, background_color=0xFFFFFFFF)
        scrollbars.set_root(self.box)

        for entry_model in self.model:
            self.add_entry(entry_model)

        dispatcher.connect(self._entry_added_cb, 'entry-added', self.model)

    def add_entry(self, entry_model):
        entry_box = hippo.CanvasBox(padding=5)
        self.box.append(entry_box)

        entry = hippo.CanvasText(text=entry_model.text,
                                 xalign=hippo.ALIGNMENT_START,
                                 size_mode=hippo.CANVAS_SIZE_WRAP_WORD)
        entry_box.append(entry)

    def _entry_added_cb(self, entry):
        self.add_entry(entry)

    def _vadj_changed_cb(self, adj):
        adj.props.value = adj.upper - adj.page_size

def get_tags():
    return [ 'log' ]

def create_view(context):
    path = os.path.join(env.get_profile_path(), 'logs', context + '.log')
    return LogView(path)
