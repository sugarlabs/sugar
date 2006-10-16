# Copyright (C) 2006, Red Hat, Inc.
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

from sugar import env

_log_writer = None

class LogWriter:
	def __init__(self, module_id):
		self._module_id = module_id

		logs_dir = os.path.join(env.get_profile_path(), 'logs')
		if not os.path.isdir(logs_dir):
			os.makedirs(logs_dir)

		log_path = os.path.join(logs_dir, module_id + '.log')
		self._log_file = open(log_path, 'w')

	def write_record(self, record):
		self.write(record.levelno, record.msg)

	def write(self, level, msg):
		fmt = "(%s): Level %s - %s\n" % (os.getpid(), level, msg)
		fmt = fmt.encode("utf8")
		self._log_file.write(fmt)

class Handler(logging.Handler):
	def __init__(self, writer):
		logging.Handler.__init__(self)

		self._writer = writer

	def emit(self, record):
		self._writer.write_record(record)

def __exception_handler(typ, exc, tb):
	trace = StringIO()
	traceback.print_exception(typ, exc, tb, None, trace)
	print >> sys.stderr, trace.getvalue()

	_log_writer.write(logging.ERROR, trace.getvalue())

def start(module_id):
	log_writer = LogWriter(module_id)

	root_logger = logging.getLogger('')
	root_logger.setLevel(logging.DEBUG)
	root_logger.addHandler(Handler(log_writer))

	global _log_writer
	_log_writer = log_writer
	sys.excepthook = __exception_handler
