import os
from ConfigParser import ConfigParser

from sugar.canvas import IconColor
from sugar import env

class _Profile:
	def __init__(self,):
		self._path = env.get_profile_path()
		self._nick_name = None
		self._color = IconColor.IconColor()

		self._ensure_dirs()		

		cp = ConfigParser()
		parsed = cp.read([self._get_config_path()])

		if cp.has_option('Buddy', 'NickName'):
			self._nick_name = cp.get('Buddy', 'NickName')
		if cp.has_option('Buddy', 'Color'):
			fill_color = cp.get('Buddy', 'Color')
			if IconColor.is_valid(fill_color):			
				self._color = IconColor.IconColor(fill_color)

	def _ensure_dirs(self):
		try:
			os.makedirs(self._path)
		except OSError, exc:
			if exc[0] != 17:  # file exists
				print "Could not create user directory."

	def get_color(self):
		return self._color

	def set_color(self, color):
		self._color = color

	def get_nick_name(self):
		return self._nick_name

	def set_nick_name(self, nick_name):
		self._nick_name = nick_name

	def get_path(self):
		return self._path

	def save(self):
		cp = ConfigParser()

		section = 'Buddy'	
		cp.add_section(section)
		cp.set(section, 'NickName', self._nick_name)
		cp.set(section, 'Color', self._color.get_fill_color())

		fileobject = open(self._get_config_path(), 'w')
		cp.write(fileobject)
		fileobject.close()

	def _get_config_path(self):
		return os.path.join(self._path, 'config')
