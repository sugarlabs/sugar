import os
from ConfigParser import ConfigParser

class Profile:
	def __init__(self):
		self._nick_name = None

	def _ensure_dirs(self):
		try:
			os.makedirs(self._path)
		except OSError, exc:
			if exc[0] != 17:  # file exists
				print "Could not create user directory."

	def get_nick_name(self):
		return self._nick_name

	def set_nick_name(self, nick_name):
		self._nick_name = nick_name
		self.save()

	def get_path(self):
		return self._path

	def read(self, profile_id):
		self._profile_id = profile_id

		base_path = os.path.expanduser('~/.sugar')
		self._path = os.path.join(base_path, profile_id)
		self._ensure_dirs()		

		cp = ConfigParser()
		parsed = cp.read([self._get_config_path()])

		if cp.has_option('Buddy', 'NickName'):
			self._nick_name = cp.get('Buddy', 'NickName')

	def save(self):
		cp = ConfigParser()

		section = 'Buddy'	
		cp.add_section(section)
		cp.set(section, 'NickName', self._nick_name)

		fileobject = open(self._get_config_path(), 'w')
		cp.write(fileobject)
		fileobject.close()

	def _get_config_path(self):
		return os.path.join(self._path, 'config')
