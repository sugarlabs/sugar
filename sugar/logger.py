"""Logging module configuration for Sugar"""
# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import sys
import os
import logging
import traceback
from cStringIO import StringIO
import time

from sugar import env

_log_writer = None

STDOUT_LEVEL = 1000
STDERR_LEVEL = 2000

formatter = logging.Formatter('%(name)s: %(message)s')

class LogWriter:
    def __init__(self, module_id):
        self._module_id = module_id

        logs_dir = _get_logs_dir()
        log_path = os.path.join(logs_dir, module_id + '.log')
        self._log_file = open(log_path, 'w')

    def write_record(self, record):
        self.write(record.levelno, formatter.format(record))

    def write(self, level, msg):
        if level == logging.ERROR:
            level_txt = 'ERROR'
        elif level == logging.WARNING:
            level_txt = 'WARNING'
        elif level == logging.DEBUG:
            level_txt = 'DEBUG'
        elif level == logging.INFO:
            level_txt = 'INFO'
        elif level == STDERR_LEVEL:
            level_txt = 'STDERR'
        elif level == STDOUT_LEVEL:
            level_txt = 'STDOUT'            

        if msg[len(msg) - 1] != '\n':
            msg += "\n"
        fmt = "%s - %s" % (level_txt, msg)
        fmt = fmt.encode("utf8")
        self._log_file.write(fmt)
        self._log_file.flush()

class Handler(logging.Handler):
    def __init__(self, writer):
        logging.Handler.__init__(self)

        self._writer = writer

    def emit(self, record):
        self._writer.write_record(record)

class StdoutCatcher:
    def write(self, txt):
        _log_writer.write(STDOUT_LEVEL, txt)
        sys.__stdout__.write(txt)

    def flush(self):
        sys.__stderr__.flush()

class StderrCatcher:
    def write(self, txt):
        _log_writer.write(STDERR_LEVEL, txt)
        sys.__stderr__.write(txt)

    def flush(self):
        sys.__stderr__.flush()

def __exception_handler(typ, exc, tb):
    trace = StringIO()
    traceback.print_exception(typ, exc, tb, None, trace)
    print >> sys.stderr, trace.getvalue()

    _log_writer.write(logging.ERROR, trace.getvalue())

def _get_logs_dir():
    logs_dir = os.path.join(env.get_profile_path(), 'logs')
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)
    return logs_dir

def start(module_id):
    log_writer = LogWriter(module_id)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(Handler(log_writer))

    sys.stdout = StdoutCatcher()
    sys.stderr = StderrCatcher()

    global _log_writer
    _log_writer = log_writer
    sys.excepthook = __exception_handler

def cleanup():
    logs_dir = _get_logs_dir()   

    # File extension for backed up logfiles.
    
    file_suffix = int(time.time())
    
    # Absolute directory path where to store old logfiles.
    # It will be created recursivly if it's not present.
    
    backup_dirpath = os.path.join(logs_dir, 'old')
    
    # How many versions shall be backed up of every logfile?
    
    num_backup_versions = 4
    
    # Make sure the backup location for old log files exists
    
    if not os.path.exists(backup_dirpath):
        os.makedirs(backup_dirpath)
    
    # Iterate over every item in 'logs' directory
    
    for filename in os.listdir(logs_dir):

        old_filepath = os.path.join(logs_dir, filename)
        
        if os.path.isfile(old_filepath):
        
            # Backup every file 
            
            new_filename = filename + '.' + str(file_suffix)
            new_filepath = os.path.join(backup_dirpath, new_filename)  
            os.rename(old_filepath, new_filepath)
    
    backup_map = {}
    
    # Temporarily map all backup logfiles
    
    for filename in os.listdir(backup_dirpath):
    
        # Remove the 'file_suffix' from the filename.
        
        end = filename.rfind(".")
        key = filename[0:end].lower()        
        key = key.replace(".", "_")
        
        if key not in backup_map:
            backup_map[key] = []
                        
        backup_list = backup_map[key]
        
        backup_list.append( os.path.join(backup_dirpath, filename) )
    
    # Only keep 'num_backup_versions' versions of every logfile.
    # Remove the others.
    
    for key in backup_map:
        backup_list = backup_map[key]           
        backup_list.sort()
        backup_list.reverse()
            
        for i in range(num_backup_versions, len(backup_list)):
            os.remove(backup_list[i])
            
