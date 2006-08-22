from sugar.conf.ActivityRegistry import ActivityRegistry
from sugar.conf.Profile import Profile

__registry = ActivityRegistry()
__profile = Profile()

def get_activity_registry():
	return __registry

def get_profile():
	return __profile
