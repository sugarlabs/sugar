import os

import geckoembed

from sugar.activity.Activity import Activity
import sugar.env

_GMAIL_ACTIVITY_TYPE = "_gmail_google._tcp"

class GMailActivity(Activity):
	def __init__(self, args):
		Activity.__init__(self, _GMAIL_ACTIVITY_TYPE)

		profile_path = os.path.join(sugar.env.get_user_dir(), 'gmail')
		geckoembed.set_profile_path(profile_path)
		self.set_title("Mail")

		embed = geckoembed.Embed()
		self.add(embed)
		embed.show()
		
		embed.load_address("http://www.gmail.com")
