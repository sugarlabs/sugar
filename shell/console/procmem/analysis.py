import proc, proc_smaps

class Analysis:
	
	pid = 0
	
	def __init__(self, pid):
		self.pid = pid
	
	def DirtyRSS(self):
		smaps =	proc_smaps.ProcSmaps(self.pid)
		dirty = []

		private = 0
		shared = 0
		
		for map in smaps.mappings:
			private += map.private_dirty
			shared  += map.shared_dirty

		dirty = {"private": int(private), "shared": int(shared)}

		return dirty
	
	def ApproxRealMemoryUsage(self):
		maps = proc_smaps.ProcMaps(self.pid)
		size = (maps.clean_size/1024)

		return size
	