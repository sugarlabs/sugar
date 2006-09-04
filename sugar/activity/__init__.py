def get_default_type(activity_type):
	"""Get the activity default type.

	   It's the type of the main network service which tracks presence
       and provides info about the activity, for example the title."""
	splitted_id = activity_type.split('.')
	splitted_id.reverse()
	return '_' + '_'.join(splitted_id) + '._udp'
