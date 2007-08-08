
import info


INTERNALS = {
            # Basic information
            'PLGNAME': "SMaps",
            'TABNAME': None, # No tabbed plugin
            'AUTHOR': "Eduardo Silva",
            'DESC': "Get dirty size and reference memory usage",

            # Plugin API
            'Plg': None, # Plugin object

            'top_data': [int, int], # Top data types needed by memphis core plugin
            'top_cols': ["PDRSS (kb)", "Referenced (kb)"]
        }
