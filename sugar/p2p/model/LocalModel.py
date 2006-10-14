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

import socket
import logging

from sugar.p2p.Notifier import Notifier
from sugar.p2p.model.AbstractModel import AbstractModel
from sugar.p2p import network

class ModelRequestHandler(object):
	def __init__(self, model):
		self._model = model

	def get_value(self, key):
		return self._model.get_value(key)

	def set_value(self, key, value):
		return self._model.set_value(key, value)

class LocalModel(AbstractModel):
	SERVICE_TYPE = "_olpc_model._tcp"

	def __init__(self, activity, pservice, service):
		AbstractModel.__init__(self)
		self._pservice = pservice
		self._activity = activity
		self._service = service
		self._values = {}
		
		self._setup_service()
		self._notifier = Notifier(service)
	
	def get_value(self, key):
		return self._values[key]
		
	def set_value(self, key, value):
		self._values[key] = value
		self._notify_model_change(key)
		self._notifier.notify(key)

	def _setup_service(self):
		self._service = self._pservice.share_activity(
						self._activity, stype = LocalModel.SERVICE_TYPE)
		self._setup_server(self._service)	

	# FIXME this is duplicated with StreamReader
	def _setup_server(self, service):
		port = service.get_port()
		logging.debug('Start model server on port %d' % (port))
		p2p_server = network.GlibXMLRPCServer(("", port))
		p2p_server.register_instance(ModelRequestHandler(self))

	def shutdown(self):
		self._pservice.unregister_service(self._service)
