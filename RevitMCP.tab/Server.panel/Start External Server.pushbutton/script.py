#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Starts the RevitMCP External CPython Server."""

# pyRevit automatically adds the extension's 'lib' folder to sys.path.
# Modules (RevitMCP_RevitListener, RevitMCP_UI) placed in 'lib' are directly importable.

print("pyRevit Button: Start External Server")

try:
    from RevitMCP_UI import ui_manager 
    ui_manager.start_external_server()
    # from pyrevit import forms
    # forms.alert("External Server start initiated. Check console for details.", title="RevitMCP")
except ImportError as e:
    print("Error importing RevitMCP_UI.ui_manager: {}. Ensure the package is in MyRevitMCP.extension/lib.".format(e))
    # from pyrevit import forms
    # forms.alert("Failed to load RevitMCP UI module. Check extension structure and logs.\nError: {}".format(e), title="RevitMCP Error")
except AttributeError as e:
    # This can happen if ui_manager was imported but start_external_server isn't found (e.g. typo)
    print("Error calling function in ui_manager: {}. Check the script.".format(e))
    # from pyrevit import forms
    # forms.alert("Error in RevitMCP UI manager script.\nError: {}".format(e), title="RevitMCP Error")
except Exception as e:
    print("An unexpected error occurred: {}".format(e))
    # from pyrevit import forms
    # forms.alert("An unexpected error occurred in RevitMCP.\nError: {}".format(e), title="RevitMCP Error") 