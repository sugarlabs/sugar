import gtk

from sugar.scene.Stage import Stage
from sugar.scene.SceneView import SceneView
from sugar.activity import Activity

class ActivityLauncher(gtk.HButtonBox):
	def __init__(self, shell):
		gtk.HButtonBox.__init__(self)

		self._shell = shell

		for module in shell.get_registry().list_activities():
			button = gtk.Button(module.get_name())
			activity_id = module.get_id()
			button.connect('clicked', self.__clicked_cb, activity_id)
			self.pack_start(button)
			button.show()

	def __clicked_cb(self, button, activity_id):
		Activity.create(activity_id)

class HomeScene(SceneView):
	def __init__(self, shell):
		self._stage = Stage()

		SceneView.__init__(self, self._stage)

		self._shell = shell

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		fixed = gtk.Fixed()

		scene = HomeScene(shell)
		fixed.put(scene, 0, 0)
		scene.show()

		launcher = ActivityLauncher(shell)
		fixed.put(launcher, 0, 0)
		launcher.show()

		self.add(fixed)
		fixed.show()
