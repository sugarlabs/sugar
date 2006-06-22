import time
import sha
import random
import binascii
import string

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

def unique_id(data = ''):
	data_string = "%s%s%s" % (time.time(), random.randint(10000, 100000), data)
	return _stringify_sha(_sha_data(data_string))


ACTIVITY_ID_LEN = 40

def is_hex(s):
	return s.strip(string.hexdigits) == ''	

def validate_activity_id(actid):
	"""Validate an activity ID."""
	if type(actid) != type("") and type(actid) != type(u""):
		return False
	if len(actid) != ACTIVITY_ID_LEN:
		return False
	if not is_hex(actid):
		return False
	return True

