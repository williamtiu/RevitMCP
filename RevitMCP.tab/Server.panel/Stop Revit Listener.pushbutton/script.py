#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Stops the RevitMCP Revit-Side Listener Server."""

print("pyRevit Button: Stop Revit Listener")

try:
    from RevitMCP_RevitListener import listener
    listener.stop_revit_listener_server()
    # from pyrevit import forms
    # forms.alert("Revit Listener server stop initiated.", title="RevitMCP")
except ImportError as e:
    print("Error importing RevitMCP_RevitListener.listener: {}. Ensure the package is in MyRevitMCP.extension/lib.".format(e))
    # from pyrevit import forms
    # forms.alert("Failed to load RevitMCP Listener module. Check extension structure and logs.\nError: {}".format(e), title="RevitMCP Error")
except Exception as e:
    print("An unexpected error occurred: {}".format(e))
    # from pyrevit import forms
    # forms.alert("An unexpected error occurred while stopping listener.\nError: {}".format(e), title="RevitMCP Error") 