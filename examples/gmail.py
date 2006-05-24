import os

import pygtk
pygtk.require('2.0')
import gtk
import geckoembed

from sugar.shell import activity
import sugar.env

class GMailActivity(activity.Activity):
	def __init__(self):
		activity.Activity.__init__(self)
	
	def activity_on_connected_to_shell(self):
		profile_path = os.path.join(sugar.env.get_user_dir(), 'gmail')
		geckoembed.set_profile_path(profile_path)
		self.activity_set_tab_text("Mail")
		self.activity_set_tab_icon_name("stock_mail")
		self.activity_show_icon(True)

		plug = self.activity_get_gtk_plug()		

		embed = geckoembed.Embed()
		plug.add(embed)
		embed.show()

		plug.show()
		
		embed.load_address("http://www.gmail.com")
		
	def activity_on_disconnected_from_shell(self):
		gtk.main_quit()
		
activity = GMailActivity()
activity.activity_connect_to_shell()

gtk.main()
