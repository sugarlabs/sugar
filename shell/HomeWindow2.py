import gtk

from sugar.scene.Stage import Stage
from sugar.scene.StageView import StageView
from sugar.scene.PixbufActor import PixbufActor
from sugar.scene.CircleLayout import CircleLayout
from sugar.scene.Group import Group
from sugar.activity import Activity
from sugar import env

class ActivityLauncher(gtk.HButtonBox):
	def __init__(self, shell):
		gtk.HButtonBox.__init__(self)

		self._shell = shell

		for module in shell.get_registry().list_activities():
			if module.get_show_launcher():
				self._add_activity(module)

	def _add_activity(self, module):
		button = gtk.Button(module.get_name())
		activity_id = module.get_id()
		button.connect('clicked', self.__clicked_cb, activity_id)
		self.pack_start(button)
		button.show()

	def __clicked_cb(self, button, activity_id):
		Activity.create(activity_id)

class HomeScene(StageView):
	def __init__(self, shell):
		self._stage = self._create_stage()
		StageView.__init__(self, self._stage)
		self._shell = shell

		launcher = ActivityLauncher(shell)
		self.put(launcher, 10, 440)
		launcher.show()

	def _create_stage(self):
		stage = Stage()

		background = env.get_data_file('home-background.png')
		pixbuf = gtk.gdk.pixbuf_new_from_file(background)
		stage.add(PixbufActor(pixbuf))

		icons_group = Group()
		icons_group.set_position(310, 80)

		pholder = env.get_data_file('activity-placeholder.png')
		pholder_pixbuf = gtk.gdk.pixbuf_new_from_file(pholder)

		i = 0
		while i < 7:
			icons_group.add(PixbufActor(pholder_pixbuf))
			i += 1

		layout = CircleLayout(110)
		icons_group.set_layout(layout)

		stage.add(icons_group)

		return stage

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		self.connect('realize', self.__realize_cb)

		fixed = gtk.Fixed()

		scene = HomeScene(shell)
		scene.set_size_request(640, 480)
		self.add(scene)
		scene.show()

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
