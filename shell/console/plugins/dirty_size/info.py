###########################################################
# Main function:
# -----------------
# self:  self plugin object
# mself: memphis object / principal class
# pinfo: row with information about current tracing process
############################################################


def plg_on_top_data_refresh(self, ppinfo):

    dirty_sizes = get_dirty(self, ppinfo['pid'])
    
    # memhis need an array 
    return [dirty_sizes['private']]

def get_dirty(pself, pid):
    ProcAnalysis = pself.INTERNALS['Plg'].proc_analysis(pid)

    return ProcAnalysis.DirtyRSS()
