from gettext import gettext as _

from sugar.activity.Activity import Activity

class GroupChatActivity(Activity):
	def __init__(self):
		Activity.__init__(self)
		self.set_title(_('Group chat'))
