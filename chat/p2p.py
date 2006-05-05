import os
import pwd
import xmlrpclib
import socket

import presence
import BuddyList
import network

class GroupRequestHandler(object):
	def __init__(self, group):
		self._group = group

	def message(self, message):
		address = network.get_authinfo()
		self._group.recv(address, message)

class Owner:
	instance = None

	def __init__(self):
		ent = pwd.getpwuid(os.getuid())
		self._nick = ent[0]
		if not self._nick or not len(self._nick):
			self._nick = "n00b"
		self._realname = ent[4]
		if not self._realname or not len(self._realname):
			self._realname = "Some Clueless User"

	def get_realname(self):
		return self._realname

	def get_nick(self):
		return self._nick

	def get_instance():
		if not Owner.instance:
			Owner.instance = Owner()
		return Owner.instance

	get_instance = staticmethod(get_instance)
		
class Group:
	instance = None

	_SERVER_PORT = 6666

	def __init__(self):
		self._pipes = {}

	def get_instance():
		if not Group.instance:
			Group.instance = Group()
			Group.instance.join()
		return Group.instance
	
	get_instance = staticmethod(get_instance)
	
	def join(self):
		self._pannounce = presence.PresenceAnnounce()

		rname = Owner.get_instance().get_realname()
		nick = Owner.get_instance().get_nick()

		self._buddy_list = BuddyList.BuddyList(rname)
		self._buddy_list.start()

		self._pannounce.register_service(rname, self._SERVER_PORT, presence.OLPC_CHAT_SERVICE,
				name = nick, realname = rname)

		self._p2p_req_handler = GroupRequestHandler(self)
		self._p2p_server = network.GlibXMLRPCServer(("", self._SERVER_PORT))
		self._p2p_server.register_instance(self._p2p_req_handler)

		self._gc_controller = network.GroupChatController('224.0.0.221', 6666, self._recv_group_message)
		self._gc_controller.start()

	def get_buddy_list(self):
		return self._buddy_list
	
	def _serialize_msg(self, pipe_id, msg):
		return pipe_id + "|" + msg

	def _deserialize_msg(self, msg):
		sep_index = msg.find("|") 
		pipe_id = msg[0 : sep_index]
		message = msg[sep_index + 1 :]
		return [pipe_id, message]
	
	def send(self, buddy, pipe_id, msg):
		addr = "http://%s:%d" % (buddy.address(), buddy.port())
		peer = xmlrpclib.ServerProxy(addr)
		success = True
		try:
			peer.message(self._serialize_msg(pipe_id, msg))
		except (socket.error, xmlrpclib.Fault), e:
			print str(e)
			success = False
		return success
	
	def broadcast(self, pipe_id, msg):
		self._gc_controller.send_msg(self._serialize_msg(pipe_id, msg))

	def register_pipe(self, input_pipe):
		self._pipes[input_pipe.get_id()] = input_pipe

	def _recv_group_message(self, msg):
		self.recv(msg['addr'], msg['data'])

	def recv(self, address, message):
		sender = self._buddy_list.find_buddy_by_address(address)
		[pipe_id, msg] = self._deserialize_msg(message)
		pipe = self._pipes[pipe_id]
		if pipe:
			pipe.recv(sender, msg)	

class AbstractPipe:
	def __init__(self, group, pipe_id=None):
		self._group = group
		self._pipe_id = pipe_id 
	
	def get_id(self):
		return self._pipe_id
	
	def send(self, msg):
		pass

class AbstractOutputPipe(AbstractPipe):
	def __init__(self, group, pipe_id=None):
		AbstractPipe.__init__(self, group, pipe_id)
	
	def send(self, msg):
		pass

class OutputPipe(AbstractOutputPipe):
	def __init__(self, group, buddy, pipe_id=None):
		AbstractOutputPipe.__init__(self, group, pipe_id)
		self._buddy = buddy
	
	def send(self, msg):
		return self._group.send(self._buddy, self._pipe_id, msg)

class BroadcastOutputPipe(AbstractOutputPipe):
	def __init__(self, group, pipe_id=None):
		AbstractOutputPipe.__init__(self, group, pipe_id)
	
	def send(self, msg):
		return self._group.broadcast(self._pipe_id, msg)
		
class InputPipe(AbstractPipe):
	def __init__(self, group, pipe_id=None):
		AbstractPipe.__init__(self, group, pipe_id)
		group.register_pipe(self)
	
	def listen(self, callback):
		self.__callback = callback
	
	def recv(self, sender, msg):
		self.__callback(sender, msg)
