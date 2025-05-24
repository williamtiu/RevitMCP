# RevitMCP: This script runs in pyRevit (IronPython). Use Python 2.7 syntax (no f-strings, use 'except Exception, e:').
# -*- coding: UTF-8 -*-
"""
Revit-Side Listener for RevitMCP (IronPython)
"""

# Import necessary Revit API modules if possible (for linting/autocomplete)
# try:
#     import Autodesk
#     import clr
#     clr.AddReference('RevitAPI')
#     clr.AddReference('RevitAPIUI')
#     from Autodesk.Revit.DB import *
#     from Autodesk.Revit.UI import *
# except ImportError:
#     print("Revit API modules not found. Running in a non-Revit environment or IronPython context needs setup.")

import os
import logging

try:
    # For Python 2.7 (IronPython)
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import json # Standard library
except ImportError:
    # Fallback for Python 3 (for local testing if needed, though target is IronPython)
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import json

import threading # Added for running server in a separate thread

# --- Logger Setup ---
# Logger instance will be configured in start_revit_listener_server
logger = logging.getLogger('RevitMCPListener')
# --- End Logger Setup ---

# --- RevitMCP Tools Import --- 
try:
    # Assuming lib folder is in the search path or sys.path is adjusted by pyRevit
    from RevitMCP_Tools import project_info_tool 
except ImportError as e:
    # Logger might not be configured yet if this fails at module import time
    # So, initial print might be necessary, or defer logging until logger is set up.
    # For now, keeping print for this initial critical failure.
    print("CRITICAL: Error importing project_info_tool: {}. Ensure it's in lib/RevitMCP_Tools and accessible.".format(e))
    project_info_tool = None # Set to None so we can check its availability
# --- End RevitMCP Tools Import ---

HOST_NAME = 'localhost'
PORT_NUMBER = 8001 # As specified in architecture.md

class RevitListenerHandler(BaseHTTPRequestHandler):
    def _set_response(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_POST(self):
        logger.info("POST request received.")
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        response_data = {}
        try:
            # IronPython json might need explicit string decode from byte array
            command_data = json.loads(post_data.decode('utf-8') if hasattr(post_data, 'decode') else post_data)
            logger.info("Received command: %s", command_data)

            # --- Command Processing Logic ---
            command_name = command_data.get("command")
            logger.debug("Extracted command_name: '%s' (Type: %s)", command_name, type(command_name))
            logger.debug("Is command_name == 'get_project_info': %s", command_name == "get_project_info")

            # Access to __revit__ context (standard in pyRevit scripts)
            # These would be None if run outside a proper pyRevit execution context.
            try:
                doc = __revit__.ActiveUIDocument.Document
                app = __revit__.Application
                logger.debug("Accessed doc and app from __revit__ context.")
            except NameError: # __revit__ is not defined
                doc = None
                app = None
                logger.warning("__revit__ context not found.")

            if command_name == "get_document_title":
                if doc:
                    doc_title = doc.Title
                    response_data = {"status": "success", "data": {"title": doc_title}}
                else:
                    response_data = {"status": "error", "message": "Revit document not accessible."}
                self._set_response()
            elif command_name == "get_selected_element_ids":
                if doc and hasattr(__revit__, 'ActiveUIDocument') and __revit__.ActiveUIDocument:
                    try:
                        selection = __revit__.ActiveUIDocument.Selection
                        element_ids = [el_id.IntegerValue for el_id in selection.GetElementIds()]
                        response_data = {"status": "success", "data": {"selected_ids": element_ids}}
                    except Exception as sel_e:
                        logger.error("Error getting selection: %s", sel_e, exc_info=True)
                        response_data = {"status": "error", "message": "Error getting selection: {}".format(sel_e)}
                else:
                    response_data = {"status": "error", "message": "Revit document or UI document not accessible for selection."}
                self._set_response()
            elif command_name == "get_revit_project_info":
                logger.info("Processing 'get_revit_project_info' command.")
                if project_info_tool and doc and app:
                    try:
                        logger.info("Attempting to call project_info_tool.get_project_information...")
                        info = project_info_tool.get_project_information(doc, app)
                        logger.info("project_info_tool.get_project_information returned: %s", info)
                        response_data = {"status": "success", "data": info}
                    except Exception as tool_e:
                        logger.error("Error executing project_info_tool: %s", tool_e, exc_info=True)
                        response_data = {"status": "error", "message": "Error executing project_info_tool: {}".format(tool_e)}
                elif not project_info_tool:
                    logger.warning("Project info tool not loaded.")
                    response_data = {"status": "error", "message": "Project info tool not loaded."}
                else: # doc or app missing
                    logger.warning("Revit document or application not accessible for project info.")
                    response_data = {"status": "error", "message": "Revit document or application not accessible for project info."}
                self._set_response()
            else:
                response_data = {"status": "error", "message": "Unknown command: {}".format(command_name)}
                self._set_response(status_code=400)
            # --- End Command Processing ---

        except Exception as e:
            logger.error("Error processing request: %s", e, exc_info=True)
            response_data = {"status": "error", "message": "Error processing request: {}".format(e)}
            self._set_response(status_code=500)
        
        logger.debug("Preparing to send response: %s", response_data)
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        logger.info("Response sent.")

# Global variable to hold the server thread instance
SERVER_THREAD = None
HTTPD_INSTANCE = None # To allow stopping it

def configure_listener_logging():
    global logger
    if not logger.handlers: # Configure only if no handlers exist
        try:
            # Use user's Documents folder instead of extension directory to avoid permission issues
            import os
            
            # Get the user's Documents folder
            try:
                # Try to get the user's Documents folder
                user_documents = os.path.expanduser("~/Documents")
                if not os.path.exists(user_documents):
                    # Fallback: try Windows Documents folder path
                    username = os.environ.get('USERNAME', 'User')
                    user_documents = os.path.join("C:", "Users", username, "Documents")
            except Exception:
                # Final fallback: use temp directory
                user_documents = os.environ.get('TEMP', 'C:\\temp')
            
            # Create RevitMCP logs directory in user's Documents
            log_dir = os.path.join(user_documents, 'RevitMCP', 'listener_logs')

            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, 'revit_listener.log')

            logger.setLevel(logging.DEBUG)
            
            # File Handler
            fh = logging.FileHandler(log_file, mode='a') # Append mode
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            
            logger.info("Revit Listener logging configured to file: %s", log_file)

        except Exception as log_e:
            # Fallback to print if logging setup fails
            print("CRITICAL: Failed to configure file logging for Revit Listener: {}".format(log_e))


def start_revit_listener_server():
    """Starts the HTTP server in a separate thread."""
    global SERVER_THREAD, HTTPD_INSTANCE, logger
    
    configure_listener_logging() # Ensure logger is configured

    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        logger.info("Listener server is already running.")
        return

    def target():
        global HTTPD_INSTANCE
        HTTPD_INSTANCE = HTTPServer((HOST_NAME, PORT_NUMBER), RevitListenerHandler)
        logger.info("Listener starting on http://%s:%s in a new thread...", HOST_NAME, PORT_NUMBER)
        HTTPD_INSTANCE.serve_forever()
        logger.info("Listener thread finished.") # Should only print if serve_forever stops

    SERVER_THREAD = threading.Thread(target=target)
    SERVER_THREAD.daemon = True  # Allow main program to exit even if thread is running
    SERVER_THREAD.start()
    logger.info("Listener server thread started.")

def stop_revit_listener_server():
    """Stops the HTTP server if it's running."""
    global SERVER_THREAD, HTTPD_INSTANCE, logger
    if HTTPD_INSTANCE:
        logger.info("Attempting to stop listener server...")
        HTTPD_INSTANCE.shutdown() # Signal serve_forever to stop
        HTTPD_INSTANCE.server_close() # Close the server socket
        HTTPD_INSTANCE = None
        logger.info("Listener server shutdown initiated.")
    else:
        logger.info("Listener server is not currently running or instance not found.")

    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        SERVER_THREAD.join(timeout=5.0) # Wait for the thread to finish
        if SERVER_THREAD.is_alive():
            logger.warning("Listener server thread did not stop in time.")
        else:
            logger.info("Listener server thread stopped.")
        SERVER_THREAD = None
    else:
        logger.info("Listener server thread is not running.")

def main(): # Kept for potential direct testing, but not primary use in pyRevit
    configure_listener_logging() # Configure logging for direct test mode too
    logger.info("Initializing listener (direct test mode)...")
    start_revit_listener_server()
    logger.info("main() function called. Server should be running in a background thread.")
    logger.info("To stop the server (direct test mode), interrupt (Ctrl+C).")
    if __name__ == "__main__":
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Stopping listener server...")
        finally:
            stop_revit_listener_server()

# This main guard is for direct execution (e.g. ipy.exe listener.py)
# For pyRevit, the button scripts will import this module and call 
# start_revit_listener_server() or stop_revit_listener_server() directly.
if __name__ == "__main__":
    main() 