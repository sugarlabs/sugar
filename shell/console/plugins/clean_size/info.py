###########################################################
# Main function:
# -----------------
# self:  self plugin object
# mself: memphis object / principal class
# pinfo: row with information about current tracing process
############################################################

def plg_on_top_data_refresh(self, pinfo):
		
	# Get clean size
	maps = self.INTERNALS['Plg'].proc_get_maps(pinfo['pid'])

	size = (maps.clean_size/1024)
	return [size]
