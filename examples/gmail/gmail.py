import os

import pygtk
pygtk.require('2.0')
import gtk
import geckoembed

from sugar.activity.Activity import Activity
import sugar.env

_GMAIL_ACTIVITY_TYPE = "_gmail_google._tcp"

class GMailActivity(Activity):
	def __init__(self):
		Activity.__init__(self, _GMAIL_ACTIVITY_TYPE)
	
	def on_connected_to_shell(self):
		profile_path = os.path.join(sugar.env.get_user_dir(), 'gmail')
		geckoembed.set_profile_path(profile_path)
		self.set_tab_text("Mail")
		self.set_tab_icon(name="stock_mail")

		plug = self.gtk_plug()		

		embed = geckoembed.Embed()
		plug.add(embed)
		embed.show()

		plug.show()
		
		embed.load_address("http://www.gmail.com")
		
activity = GMailActivity()
activity.connect_to_shell()

gtk.main()
