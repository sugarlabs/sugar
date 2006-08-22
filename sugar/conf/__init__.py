from sugar.conf.ActivityRegistry import ActivityRegistry

__registry = ActivityRegistry()

def get_activity_registry():
	return __registry
