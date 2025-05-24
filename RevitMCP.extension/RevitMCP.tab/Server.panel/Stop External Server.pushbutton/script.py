# RevitMCP: This script runs in pyRevit (IronPython). Use Python 2.7 syntax (no f-strings, use 'except Exception, e:').
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Stops the RevitMCP External CPython Server."""

print("pyRevit Button: Stop External Server")

try:
    from RevitMCP_UI import ui_manager
    ui_manager.stop_external_server()
    # from pyrevit import forms
    # forms.alert("External Server stop initiated.", title="RevitMCP")
except ImportError as e:
    print("Error importing RevitMCP_UI.ui_manager: {}. Ensure the package is in MyRevitMCP.extension/lib.".format(e))
    # from pyrevit import forms
    # forms.alert("Failed to load RevitMCP UI module. Check extension structure and logs.\nError: {}".format(e), title="RevitMCP Error")
except Exception as e:
    print("An unexpected error occurred: {}".format(e))
    # from pyrevit import forms
    # forms.alert("An unexpected error occurred in RevitMCP.\nError: {}".format(e), title="RevitMCP Error") 