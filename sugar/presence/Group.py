import Service
import sha
import binascii
import time


def is_group_service_type(stype):
	"""Return True if the service type matches a group
	service type, or False if it does not."""
	if stype.endswith("_group_olpc._tcp") or stype.endswith("_group_olpc._udp"):
		return True
	return False


def _stringify_sha(sha_hash):
	"""Convert binary sha1 hash data into printable characters."""
	print_sha = ""
	for char in sha_hash:
		print_sha = print_sha + binascii.b2a_hex(char)
	return print_sha

def _sha_data(data):
	"""sha1 hash some bytes."""
	sha_hash = sha.new()
	sha_hash.update(data)
	return sha_hash.digest()


__GROUP_NAME_TAG = "Name"
__GROUP_RESOURCE_TAG = "Resource"

def new_group_service(group_name, resource):
	"""Create a new service suitable for defining a new group."""
	if type(group_name) != type("") or not len(group_name):
		raise ValueError("group name must be a valid string.")
	if type(resource) != type("") or not len(resource):
		raise ValueError("group resource must be a valid string.")

	# Create a randomized service type
	data_string = "%s%s%s%s" % (time.time(), random.randint(10000, 100000), \
			group_name, resource)
	hash_string = _stringify_sha(_sha_data(data_string))
	stype = "_%s_group_olpc._udp" % hash_string

	properties = {__GROUP_NAME_TAG: group_name, __GROUP_RESOURCE_TAG: resource }
	owner_nick = ""
	port = random.randint(5000, 65000)
	# Use random currently unassigned multicast address
	address = "232.%d.%d.%d" % (random.randint(0, 254), random.randint(1, 254),
			random.randint(1, 254))
	service = Service.Service(owner_nick, stype, "local", address=address,
			port=port, properties=properties)
	return service


class Group(object):
	"""Represents a collection of buddies all interested in the same resource."""
	def __init__(self, service):
		if not isinstance(service, Service.Service):
			raise ValueError("service argument was not a Service object.")
		if not service.is_group_service():
			raise ValueError("provided serivce was not a group service.")
		name = service.get_one_property(__GROUP_NAME_TAG)
		if name == None:
			raise ValueError("provided service did not provide a group name.")
		self._name = name
		resource = service.get_one_property(__GROUP_RESOURCE_TAG)
		if resource == None:
			raise ValueError("provided service did not provide a group resource.")
		self._resource = resource
		self._service = service

	def get_name(self):
		return self._name

	def get_service(self):
		return self._service

	def get_resource(self):
		return self._resource
