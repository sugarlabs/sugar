###########################################################
# Main function:
# -----------------
# self:  self plugin object
# mself: memphis object / principal class
# pinfo: row with information about current tracing process
############################################################

def plg_on_top_data_refresh(self, ppinfo):

    data = [ppinfo['pid'], ppinfo['name'], ppinfo['state_name']]
        
    return data
