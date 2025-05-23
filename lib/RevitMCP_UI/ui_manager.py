"""
Revit UI Launcher & Manager for RevitMCP (pyRevit)

This script will be part of a pyRevit extension's lib folder and will be responsible for:
- Providing functions to start/stop the external CPython server.
- Detecting a suitable CPython environment.
"""

import subprocess
import os
import sys
# import shutil # For finding executables
import json
import tempfile

# --- Configuration ---

# When this script (ui_manager.py) is in MyRevitMCP.extension/lib/RevitMCP_UI/,
# __file__ is .../lib/RevitMCP_UI/ui_manager.py
# os.path.dirname(__file__) is .../lib/RevitMCP_UI/
# We need to get to .../lib/RevitMCP_ExternalServer/server.py

# Path to the root of the 'lib' directory for this extension.
# This assumes ui_manager.py is in lib/RevitMCP_UI/
LIB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXTERNAL_SERVER_SCRIPT_PATH = os.path.join(LIB_ROOT, "RevitMCP_ExternalServer", "server.py")

# User-configurable CPython executable path.
# If this is set to a valid Python 3.7+ executable, it will be used.
# Otherwise, the script will attempt to find a suitable Python in PATH.
CPYTHON_EXECUTABLE_OVERRIDE = "" # Example: "C:/Python311/python.exe" or "/usr/bin/python3.11"

SERVER_PROCESS = None
DETECTED_CPYTHON_EXECUTABLE = None # Stores the path found by auto-detection or override

MIN_PYTHON_VERSION = (3, 7)
REQUIRED_PACKAGES = ["flask", "requests"]

# --- Helper Functions ---

def _is_windows():
    return os.name == 'nt'

def _check_python_environment(python_exe):
    """Checks if the given Python executable meets version and package requirements."""
    if not python_exe or not os.path.exists(python_exe):
        return False, "Python executable not found."

    # This is the main try block for the function
    try: 
        # Check version
        cmd_version = [python_exe, "-c", "import sys; import json; print(json.dumps(sys.version_info))"]
        proc_version = subprocess.Popen(cmd_version, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = proc_version.communicate()
        
        if proc_version.returncode != 0:
            stderr_decoded = stderr_bytes.decode(sys.getfilesystemencoding() or 'utf-8').strip()
            return False, "Error checking Python version ({}): {}".format(python_exe, stderr_decoded or "No stderr output")

        version_out_decoded = stdout_bytes.decode(sys.getfilesystemencoding() or 'utf-8').strip()
        version_info = json.loads(version_out_decoded)
        py_version = tuple(version_info[:3])

        if py_version < MIN_PYTHON_VERSION:
            return False, "Python version {}.{}.{} is older than required {}.{}.{}".format(
                py_version[0], py_version[1], py_version[2],
                MIN_PYTHON_VERSION[0], MIN_PYTHON_VERSION[1], MIN_PYTHON_VERSION[2] if len(MIN_PYTHON_VERSION) > 2 else ''
            )

        # Check required packages using a temporary script file for robustness
        script_lines = ["import sys"]
        for pkg in REQUIRED_PACKAGES:
            # Correctly form the multi-line string for the script content
            script_lines.append((
                "try:\n"
                "    import {}\n"
                "except ImportError:\n"
                "    sys.exit(1)").format(pkg))
        script_lines.append("sys.exit(0)")
        check_script_py_content = "\n".join(script_lines)

        temp_file_handle_unused, temp_file_path = tempfile.mkstemp(suffix=".py")
        if temp_file_handle_unused is not None:
            try:
                os.close(temp_file_handle_unused)
            except OSError:
                pass 

        # Inner try-finally for temp file management, nested inside the main try block
        try: 
            try:
                with open(temp_file_path, 'wb') as f:
                    f.write(check_script_py_content.encode('utf-8'))
            except IOError as e:
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass
                return False, "Failed to write package check script: {}".format(e)

            cmd_packages = [python_exe, temp_file_path]
            proc_packages = subprocess.Popen(cmd_packages, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout_pkg_bytes, stderr_pkg_bytes = proc_packages.communicate()
            
            if proc_packages.returncode != 0:
                stderr_pkg_decoded = stderr_pkg_bytes.decode(sys.getfilesystemencoding() or 'utf-8').strip()
                details_msg = stderr_pkg_decoded
                if not details_msg:
                    details_msg = "Package check script failed (exit code {}). Script content was:\n{}".format(proc_packages.returncode, check_script_py_content)
                
                missing_pkgs_str = "Required packages ({}) not found. Install with: {} -m pip install {}. Details: {}".format(
                    ', '.join(REQUIRED_PACKAGES),
                    python_exe,
                    ' '.join(REQUIRED_PACKAGES),
                    details_msg
                )
                return False, missing_pkgs_str
        finally:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    print("Warning: Failed to remove temporary script file {}: {}".format(temp_file_path, e))
            
        # If all checks passed in the main try block
        return True, "Valid: {} (Version: {}.{}.{})".format(
            python_exe, py_version[0], py_version[1], py_version[2]
        )

    # These except clauses now correctly pair with the main try block
    except (IOError, OSError) as e: 
        return False, "OS error when trying to run {}: {}".format(python_exe, str(e))
    except ValueError as e: 
        return False, "Error parsing version output from {}: {}".format(python_exe, str(e))
    except Exception as e:
        return False, "Unexpected error checking {}: {}".format(python_exe, str(e))

def find_cpython_executable():
    """
    Attempts to find a suitable CPython executable.
    1. Uses CPYTHON_EXECUTABLE_OVERRIDE if set and valid.
    2. Searches PATH for common Python commands.
    Returns the path to a suitable executable or None.
    """
    global DETECTED_CPYTHON_EXECUTABLE
    if DETECTED_CPYTHON_EXECUTABLE: # Already found
        return DETECTED_CPYTHON_EXECUTABLE

    # import shutil # Moved import here # KEEP THIS COMMENTED or remove, it's duplicated
    import shutil # Ensure shutil is imported for the primary attempt

    # 1. Check override
    if CPYTHON_EXECUTABLE_OVERRIDE and CPYTHON_EXECUTABLE_OVERRIDE != "PLEASE_CONFIGURE_THIS":
        is_valid, msg = _check_python_environment(CPYTHON_EXECUTABLE_OVERRIDE)
        if is_valid:
            print("Using configured CPYTHON_EXECUTABLE_OVERRIDE: {}".format(msg))
            DETECTED_CPYTHON_EXECUTABLE = CPYTHON_EXECUTABLE_OVERRIDE
            return DETECTED_CPYTHON_EXECUTABLE
        else:
            print("Warning: CPYTHON_EXECUTABLE_OVERRIDE ('{}') is not valid or does not meet requirements: {}".format(CPYTHON_EXECUTABLE_OVERRIDE, msg))
            print("Attempting to find Python in PATH...")

    # 2. Search PATH
    common_names = ["python3", "python"]
    if _is_windows():
        common_names = ["python.exe", "python3.exe"] + common_names 

    for name in common_names:
        found_path = None
        try:
            found_path = shutil.which(name)
        except AttributeError:
            # shutil.which might not be available in IronPython's shutil
            print("shutil.which not available. Attempting fallback for '{}'.".format(name))
            if _is_windows():
                try:
                    # Use 'where' command on Windows
                    # On Windows, subprocess.check_output with shell=True often prefers a string command.
                    command_str = 'where {}'.format(name)
                    # In Python 2.7 (IronPython), check_output returns bytes, so decode it.
                    # It also doesn't have a 'text' argument.
                    output_bytes = subprocess.check_output(command_str, shell=True)
                    output_str = output_bytes.decode(sys.getfilesystemencoding() or 'utf-8')
                    
                    # 'where' can return multiple paths, one per line. Take the first one.
                    # It can also return an informational message if not found, which might not be an error.
                    lines = output_str.strip().splitlines()
                    if lines:
                        first_path = lines[0].strip()
                        if os.path.exists(first_path): # Double check the path from where output
                            found_path = first_path
                            print("Found '{}' using 'where': {}".format(name, found_path))
                        else:
                            print("'where' command output for '{}' ('{}') is not a valid path.".format(name, first_path))
                    else:
                        print("'where' command for '{}' produced no output.".format(name))

                except subprocess.CalledProcessError as e:
                    # This means 'where' command itself ran but returned a non-zero exit code (e.g., file not found)
                    print("'where {}' command failed (returned non-zero): {}".format(name, e))
                except (IOError, OSError) as e: # Changed FileNotFoundError to IOError/OSError for Py2.7
                    # This can happen if 'where' command is not found, or other OS level errors
                    print("Fallback 'where {}' OS error: {}".format(name, e))
            else:
                # On non-Windows, if shutil.which is missing, we don't have an easy built-in alternative here.
                # The original code didn't have a non-shutil.which path for non-Windows anyway.
                print("shutil.which not available and not on Windows. Cannot auto-detect Python path this way.")

        if found_path:
            print("Found '{}' at '{}'. Checking environment...".format(name, found_path))
            is_valid, msg = _check_python_environment(found_path)
            if is_valid:
                print("Using automatically detected Python: {}".format(msg))
                DETECTED_CPYTHON_EXECUTABLE = found_path
                return DETECTED_CPYTHON_EXECUTABLE
            else:
                print("Skipping '{}': {}".format(found_path, msg))
    
    err_msg_parts = [
        "Error: Could not automatically find a suitable CPython {}.{}+ executable with Flask and Requests installed.".format(MIN_PYTHON_VERSION[0], MIN_PYTHON_VERSION[1]),
        "Please do one of the following:",
        "1. Install Python {}.{} or newer.".format(MIN_PYTHON_VERSION[0], MIN_PYTHON_VERSION[1]),
        "2. Ensure Flask and Requests are installed in that Python environment (e.g., 'pip install flask requests').",
        "3. Manually set the 'CPYTHON_EXECUTABLE_OVERRIDE' variable in the RevitMCP_UI/ui_manager.py script to the full path of your Python executable."
    ]
    full_err_msg = '\n'.join(err_msg_parts)
    print(full_err_msg)
    DETECTED_CPYTHON_EXECUTABLE = None
    return None

def get_pyrevit_forms():
    """Safely import and return pyrevit.forms if available."""
    try:
        from pyrevit import forms
        return forms
    except ImportError:
        return None

def show_alert(message, title="RevitMCP"):
    forms = get_pyrevit_forms()
    if forms:
        forms.alert(message, title=title)
    else:
        print("[{}] {}".format(title, message))

def start_external_server():
    global SERVER_PROCESS
    
    python_exe_to_use = find_cpython_executable()
    if not python_exe_to_use:
        show_alert("CPython executable not found or not configured correctly. Please check logs/console and configure 'CPYTHON_EXECUTABLE_OVERRIDE' in ui_manager.py if needed.", title="RevitMCP Error")
        return

    if not os.path.exists(EXTERNAL_SERVER_SCRIPT_PATH):
        error_msg = "External server script not found: {}".format(EXTERNAL_SERVER_SCRIPT_PATH)
        print(error_msg)
        show_alert(error_msg, title="Error")
        return

    if SERVER_PROCESS is None or SERVER_PROCESS.poll() is not None:
        print("Starting RevitMCP External Server from: {}".format(EXTERNAL_SERVER_SCRIPT_PATH))
        print("Using Python executable: {}".format(python_exe_to_use))
        try:
            SERVER_PROCESS = subprocess.Popen([python_exe_to_use, EXTERNAL_SERVER_SCRIPT_PATH])
            success_msg = "RevitMCP External Server process started. PID: {}".format(SERVER_PROCESS.pid)
            print(success_msg)
            show_alert(success_msg)
        except FileNotFoundError: 
            error_msg = "Error: The Python executable '{}' was not found. This should not happen if find_cpython_executable worked.".format(python_exe_to_use)
            print(error_msg)
            show_alert(error_msg, title="Error")
            SERVER_PROCESS = None
        except Exception as e:
            error_msg = "Failed to start RevitMCP External Server: {}".format(e)
            print(error_msg)
            show_alert(error_msg, title="Error")
            SERVER_PROCESS = None
    else:
        running_msg = "RevitMCP External Server is already running."
        print(running_msg)
        show_alert(running_msg)

def stop_external_server():
    global SERVER_PROCESS
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
        print("Stopping RevitMCP External Server...")
        SERVER_PROCESS.terminate()
        try:
            SERVER_PROCESS.wait(timeout=5)
            stopped_msg = "RevitMCP External Server stopped."
            print(stopped_msg)
            show_alert(stopped_msg)
        except subprocess.TimeoutExpired:
            print("Server did not terminate in time, killing...")
            SERVER_PROCESS.kill()
            killed_msg = "RevitMCP External Server forcefully stopped."
            print(killed_msg)
            show_alert(killed_msg)
        SERVER_PROCESS = None
    else:
        not_running_msg = "RevitMCP External Server is not running."
        print(not_running_msg)
        show_alert(not_running_msg)

# Test block for when script is run directly (e.g. for development)
# This part won't run when imported by pyRevit button scripts.
if __name__ == "__main__":
    print("RevitMCP UI Manager - Direct Test Mode (from within lib/RevitMCP_UI)")
    print("---------------------------------------------------------------------")
    print("LIB_ROOT: {}".format(LIB_ROOT))
    print("External Server Script: {}".format(EXTERNAL_SERVER_SCRIPT_PATH))
    print("---------------------------------------------------------------------")
    print("Attempting to find suitable CPython...")
    
    found_python = find_cpython_executable()
    if found_python:
        print("Found suitable Python for testing: {}".format(found_python))
        print("To test server start/stop, uncomment the lines below.")
        print("Ensure Flask & Requests are installed in the CPython env: {} -m pip install flask requests".format(found_python))
        # print("\n--- Simulating Server Start ---")
        # start_external_server()
        # if SERVER_PROCESS:
        #     print("Server presumably running (PID: {}). Check console output from external server.".format(SERVER_PROCESS.pid))
        #     input("Press Enter to stop server...")
        #     stop_external_server()
        # else:
        #     print("Server did not start. Check error messages above.")
    else:
        print("Could not find a suitable Python executable for testing the server start.")
        print("Please configure CPYTHON_EXECUTABLE_OVERRIDE or ensure Python 3.7+ with Flask & Requests is in PATH.")

    print("\nTest mode finished.")

# --- For actual pyRevit integration ---
# The following would be in separate script.py files for each pushbutton

# Example for StartServer.pushbutton/script.py:
# ```python
# #!/usr/bin/python
# # -*- coding: UTF-8 -*-
# from RevitMCP_UI import ui_manager # Assuming RevitMCP_UI is in a path recognized by pyRevit
# ui_manager.start_external_server()
# ```

# Example for StopServer.pushbutton/script.py:
# ```python
# #!/usr/bin/python
# # -*- coding: UTF-8 -*-
# from RevitMCP_UI import ui_manager
# ui_manager.stop_external_server()
# ``` 