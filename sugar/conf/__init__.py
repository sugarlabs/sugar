from sugar.conf.ActivityRegistry import _ActivityRegistry
from sugar.conf.Profile import Profile

__registry = _ActivityRegistry()
__profile = Profile()

def get_activity_registry():
	return __registry

def get_profile():
	return __profile
