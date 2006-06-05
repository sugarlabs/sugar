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
	
	def on_connected_to_shell(self):
		profile_path = os.path.join(sugar.env.get_user_dir(), 'gmail')
		geckoembed.set_profile_path(profile_path)
		self.set_tab_text("Mail")
		self.set_tab_icon(name="stock_mail")
		self.set_show_icon(True)

		plug = self.gtk_plug()		

		embed = geckoembed.Embed()
		plug.add(embed)
		embed.show()

		plug.show()
		
		embed.load_address("http://www.gmail.com")
		
	def on_disconnected_from_shell(self):
		gtk.main_quit()
		
activity = GMailActivity()
activity.connect_to_shell()

gtk.main()
