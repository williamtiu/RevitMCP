#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Starts the RevitMCP Revit-Side Listener Server."""

# pyRevit automatically adds the extension's 'lib' folder to sys.path.
# Modules (RevitMCP_RevitListener, RevitMCP_UI) placed in 'lib' are directly importable.

print("pyRevit Button: Start Revit Listener")

try:
    from RevitMCP_RevitListener import listener 
    listener.start_revit_listener_server()
    # from pyrevit import forms 
    # forms.alert("Revit Listener server started (or was already running).", title="RevitMCP")
except ImportError as e:
    print("Error importing RevitMCP_RevitListener.listener: {}. Ensure the package is in MyRevitMCP.extension/lib.".format(e))
    # from pyrevit import forms
    # forms.alert("Failed to load RevitMCP Listener module. Check extension structure and logs.\nError: {}".format(e), title="RevitMCP Error")
except Exception as e:
    print("An unexpected error occurred: {}".format(e))
    # from pyrevit import forms
    # forms.alert("An unexpected error occurred while starting listener.\nError: {}".format(e), title="RevitMCP Error") 