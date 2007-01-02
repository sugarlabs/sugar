import info

INTERNALS = {
            'PLGNAME': "memphis",
            'TABNAME': None,
            'AUTHOR': "Eduardo Silva",
            'DESC': "Print basic process information",

            # Plugin API
            'Plg': None, # Plugin object

            # Top process view requirements
            'top_data': [int, str, str], # Top data types needed by memphis core plugin
            'top_cols': ["PID", "Process Name", "Status"] # Column names
        }
