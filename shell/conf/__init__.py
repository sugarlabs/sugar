from conf.ActivityRegistry import _ActivityRegistry
from conf.Profile import _Profile

__registry = _ActivityRegistry()
__profile = _Profile()

def get_activity_registry():
	return __registry

def get_profile():
	return __profile
