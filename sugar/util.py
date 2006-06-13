import time
import sha
import random
import binascii

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
