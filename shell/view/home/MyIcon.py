import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor

class MyIcon(IconItem):
	def __init__(self, size):
		profile = conf.get_profile()

		IconItem.__init__(self, icon_name='stock-buddy',
					  	  color=profile.get_color(), size=size)
