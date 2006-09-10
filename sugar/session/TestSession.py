from sugar.session.DbusProcess import DbusProcess
from sugar import env

class TestSession:
	def start(self):
		env.setup_python_path()

		process = DbusProcess()
		process.start()
