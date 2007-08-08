###########################################################
# Main function:
# -----------------
# self:  self plugin object
# mself: memphis object / principal class
# pinfo: row with information about current tracing process
############################################################


def plg_on_top_data_refresh(self, ppinfo):
    smaps = get_data(self, ppinfo['pid'])
    
    # memphis need an array 
    return [smaps['private_dirty'], smaps['referenced']]

def get_data(pself, pid):
    ProcAnalysis = pself.INTERNALS['Plg'].proc_analysis(pid)

    return ProcAnalysis.SMaps()
