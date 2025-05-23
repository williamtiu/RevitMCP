import sys
import os

# Path to the listener module we are interested in
# Ensure this path is exactly correct for your system
listener_module_path_expected = r"C:\Users\jacob\AppData\Roaming\pyRevit-Master\extensions\MyRevitMCP.extension\lib\RevitMCP_RevitListener\listener.py"

print("--- Listener Module Debug ---")
print("Python sys.version: {}".format(sys.version))
print("Python sys.executable: {}".format(sys.executable))
print("Current Working Directory: {}".format(os.getcwd()))

# Determine the module name as it would appear in sys.modules
# This depends on how pyRevit structures its imports from the 'lib' folder.
# Common patterns might be 'MyRevitMCP.lib.RevitMCP_RevitListener.listener' 
# or 'RevitMCP_RevitListener.listener' if 'lib' is directly on sys.path.
# Let's try a few common ones or inspect sys.modules directly.

# For safety, let's iterate sys.modules to find it if its exact name is uncertain
found_module_in_sys_modules = None
actual_module_name_in_sys = None

for name, module_obj in sys.modules.items():
    if hasattr(module_obj, '__file__') and module_obj.__file__ is not None:
        # Normalize paths for comparison
        try:
            normalized_module_file = os.path.normpath(module_obj.__file__)
            normalized_expected_path = os.path.normpath(listener_module_path_expected)
            if normalized_module_file == normalized_expected_path:
                found_module_in_sys_modules = module_obj
                actual_module_name_in_sys = name
                break
        except Exception as e: # Handle potential errors with os.path.normpath if __file__ is unusual
            print("Error normalizing path for module {}: {} - {}".format(name, module_obj.__file__, e))


if found_module_in_sys_modules:
    print("Module with path '{}' IS in sys.modules under the name: '{}'.".format(listener_module_path_expected, actual_module_name_in_sys))
    module_instance = found_module_in_sys_modules
    if hasattr(module_instance, '__file__') and module_instance.__file__: # Redundant check, but safe
        print("  sys.modules['{}'].__file__ is: {}".format(actual_module_name_in_sys, module_instance.__file__))
        
        try:
            with open(module_instance.__file__, 'r') as f:
                lines = f.readlines()
                expected_line_fragment = 'elif command_name == "get_revit_project_info":'
                corrected_log_fragment = "Processing 'get_revit_project_info' command."
                
                found_elif = False
                found_log = False

                for i, line in enumerate(lines):
                    if expected_line_fragment in line:
                        print("  Found expected ELIF fragment '{}' at line {} in {}".format(expected_line_fragment, i+1, module_instance.__file__))
                        found_elif = True
                    if corrected_log_fragment in line:
                        print("  Found expected LOG fragment '{}' at line {} in {}".format(corrected_log_fragment, i+1, module_instance.__file__))
                        found_log = True
                
                if not found_elif:
                    print("  ERROR: Did NOT find expected ELIF fragment '{}' in {} loaded by sys.modules!".format(expected_line_fragment, module_instance.__file__))
                if not found_log:
                    print("  ERROR: Did NOT find expected LOG fragment '{}' in {} loaded by sys.modules!".format(corrected_log_fragment, module_instance.__file__))

        except Exception as e:
            print("  Error reading module file {}: {}".format(module_instance.__file__, e))
            
    else: # Should not happen if found_module_in_sys_modules is true and __file__ was checked
        print("  sys.modules['{}'] does not have a __file__ attribute (this is unexpected).".format(actual_module_name_in_sys))
else:
    print("Module with path '{}' is NOT in sys.modules.".format(listener_module_path_expected))
    print("  This suggests Revit is not using a module loaded from this exact file path, or it's not loaded in a standard way into sys.modules.")

print("\nChecking expected file path directly on disk:")
if os.path.exists(listener_module_path_expected):
    print("Expected file '{}' EXISTS on disk.".format(listener_module_path_expected))
    try:
        with open(listener_module_path_expected, 'r') as f:
            lines = f.readlines()
            expected_line_fragment = 'elif command_name == "get_revit_project_info":'
            corrected_log_fragment = "Processing 'get_revit_project_info' command."
            
            found_elif_disk = False
            found_log_disk = False

            for i, line in enumerate(lines):
                if expected_line_fragment in line:
                    print("  Found expected ELIF fragment '{}' at line {} in ON DISK file.".format(expected_line_fragment, i+1))
                    found_elif_disk = True
                if corrected_log_fragment in line:
                    print("  Found expected LOG fragment '{}' at line {} in ON DISK file.".format(corrected_log_fragment, i+1))
                    found_log_disk = True

            if not found_elif_disk:
                print("  ERROR: Did NOT find expected ELIF fragment '{}' in the ON DISK file!".format(expected_line_fragment))
            if not found_log_disk:
                print("  ERROR: Did NOT find expected LOG fragment '{}' in the ON DISK file!".format(corrected_log_fragment))
    except Exception as e:
        print("  Error reading ON DISK file {}: {}".format(listener_module_path_expected, e))
else:
    print("Expected file '{}' DOES NOT EXIST on disk.".format(listener_module_path_expected))

print("--- End Listener Module Debug ---") 