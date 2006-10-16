from conf.ActivityRegistry import _ActivityRegistry

_activity_registry = _ActivityRegistry()

def get_activity_registry():
	return _activity_registry
