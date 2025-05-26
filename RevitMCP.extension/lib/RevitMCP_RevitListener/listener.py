# RevitMCP: This script runs in pyRevit (IronPython). Use Python 2.7 syntax (no f-strings, use 'except Exception, e:').
# -*- coding: UTF-8 -*-
"""
Revit-Side Listener for RevitMCP (IronPython)
"""

# --- Revit API Imports ---
# It's good practice to have these for clarity and potential linting, 
# even if pyRevit injects them globally.
try:
    import clr
    clr.AddReference('RevitAPI')
    clr.AddReference('RevitAPIUI')
    import Autodesk
    from Autodesk.Revit.DB import (
        FilteredElementCollector, 
        View, # Assuming this is DB.View, adjust if it's Autodesk.Revit.DB.View directly
        ImageExportOptions, 
        ImageFileType, 
        ImageResolution, # Added
        ExportRange, 
        ZoomFitType, 
        ElementId
    )
    from Autodesk.Revit.UI import TaskDialog # Example UI import, not used yet
    # For List[ElementId]
    from System.Collections.Generic import List
except ImportError:
    print("Revit API modules not found. Ensure script is run in a Revit environment.")
    # Define placeholders if script needs to be parsable outside Revit for some reason
    # This is generally not recommended for production pyRevit scripts.
    class DB: pass
    class UI: pass 
# --- End Revit API Imports ---

import os
import logging
import tempfile # Added for view export
import base64   # Added for view export

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
        post_data_bytes = self.rfile.read(content_length)
        
        response_data = {}
        try:
            command_data_str = post_data_bytes.decode('utf-8') if hasattr(post_data_bytes, 'decode') else post_data_bytes
            command_data = json.loads(command_data_str)
            logger.info("Received command data: %s", command_data)

            command_name = command_data.get("command")
            logger.debug("Extracted command_name: '%s'", command_name)

            doc = None
            app = None
            try:
                doc = __revit__.ActiveUIDocument.Document
                app = __revit__.Application
                logger.debug("Accessed doc and app from __revit__ context.")
            except NameError: 
                logger.warning("__revit__ context not found. Cannot access Revit document or application.")
                # For commands that don't need doc/app, this might be fine. For others, it's an error.

            if not doc or not app:
                # Check if the command requires doc/app. If so, return error early.
                commands_requiring_revit_context = ["get_document_title", "get_selected_element_ids", "get_revit_project_info", "export_revit_view"]
                if command_name in commands_requiring_revit_context:
                    response_data = {"status": "error", "message": "Revit document or application not accessible via __revit__ context."}
                    self._set_response(status_code=500)
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    logger.error("Command '%s' requires Revit context, but it was not found.", command_name)
                    return
            
            # --- Command Processing Logic ---
            if command_name == "get_document_title":
                doc_title = doc.Title # Assumes doc is available due to check above
                response_data = {"status": "success", "data": {"title": doc_title}}
                self._set_response()

            elif command_name == "get_selected_element_ids":
                # Assumes doc and __revit__.ActiveUIDocument are available
                try:
                    selection = __revit__.ActiveUIDocument.Selection
                    element_ids = [el_id.IntegerValue for el_id in selection.GetElementIds()]
                    response_data = {"status": "success", "data": {"selected_ids": element_ids}}
                except Exception as sel_e:
                    logger.error("Error getting selection: %s", sel_e, exc_info=True)
                    response_data = {"status": "error", "message": "Error getting selection: {}".format(sel_e)}
                self._set_response()

            elif command_name == "get_revit_project_info":
                logger.info("Processing 'get_revit_project_info' command.")
                if project_info_tool: # Assumes doc & app are available
                    try:
                        info = project_info_tool.get_project_information(doc, app)
                        response_data = {"status": "success", "data": info}
                    except Exception as tool_e:
                        logger.error("Error executing project_info_tool: %s", tool_e, exc_info=True)
                        response_data = {"status": "error", "message": "Error executing project_info_tool: {}".format(tool_e)}
                else:
                    response_data = {"status": "error", "message": "Project info tool not loaded."}
                self._set_response()

            elif command_name == "export_revit_view":
                logger.info("Processing 'export_revit_view' command.")
                # view_name should be passed in the main payload, alongside "command"
                view_name_to_export = command_data.get("view_name") 

                if not view_name_to_export:
                    response_data = {"status": "error", "message": "View name not provided for export."}
                    self._set_response(status_code=400)
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    return
                else:
                    try:
                        output_folder = os.path.join(tempfile.gettempdir(), "RevitMCPExports")
                        if not os.path.exists(output_folder):
                            os.makedirs(output_folder)
                        
                        # Create a filename prefix that is less likely to clash if view names are similar
                        # Using a simple prefix for now as Revit appends the view name anyway.
                        file_path_prefix = os.path.join(output_folder, "revit_export") 
                        
                        target_view = None
                        # Ensure View is correctly referenced (e.g. Autodesk.Revit.DB.View or just View if imported)
                        all_views = FilteredElementCollector(doc).OfClass(Autodesk.Revit.DB.View).ToElements()
                        for view_element in all_views:
                            if view_element.Name == view_name_to_export:
                                target_view = view_element
                                break
                        
                        if not target_view:
                            response_data = {"status": "error", "message": "View '{}' not found.".format(view_name_to_export)}
                            self._set_response(status_code=404)
                            self.wfile.write(json.dumps(response_data).encode('utf-8'))
                            return
                        else:
                            logger.info("Found view '{}' (ID: {}). Preparing export.".format(target_view.Name, target_view.Id.ToString()))
                            ieo = ImageExportOptions()
                            ieo.ExportRange = ExportRange.SetOfViews
                            viewIds = List[ElementId]() 
                            viewIds.Add(target_view.Id)
                            ieo.SetViewsAndSheets(viewIds)
                            ieo.FilePath = file_path_prefix 
                            ieo.HLRandWFViewsFileType = ImageFileType.PNG
                            ieo.ShadowViewsFileType = ImageFileType.PNG 
                            ieo.ImageResolution = ImageResolution.DPI_150
                            ieo.ZoomType = ZoomFitType.Zoom 
                            ieo.Zoom = 100 
                            
                            # Ensure the view is suitable for export (e.g., not a schedule, legend without items might error)
                            if not target_view.CanBePrinted:
                                logger.warning("View '{}' cannot be printed/exported.".format(view_name_to_export))
                                response_data = {"status": "error", "message": "View '{}' cannot be printed or exported.".format(view_name_to_export)}
                                self._set_response(status_code=400)
                                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                                return
                            else:
                                logger.info("Exporting image with options: FilePath='{}', Resolution='{}', ZoomType='{}', Zoom='{}'".format(ieo.FilePath, ieo.ImageResolution, ieo.ZoomType, ieo.Zoom))
                                doc.ExportImage(ieo)
                                logger.info("doc.ExportImage() completed.")

                                # Revit typically appends the view name to the FilePath if FilePath is a prefix.
                                # Example: if FilePath is "C:\\temp\\export", output is "C:\\temp\\export-ViewName.png"
                                # If FilePath is "C:\\temp\\export.png", output is "C:\\temp\\export.png"
                                # Using a robust find method:
                                exported_file_path_actual = ieo.GetSavedFileName(doc, target_view.Id) # Preferred way if API supports it
                                if not exported_file_path_actual or not os.path.exists(exported_file_path_actual):
                                    # Fallback to finding the newest PNG if GetSavedFileName isn't available/reliable for this context
                                    logger.warning("GetSavedFileName did not return a valid path. Trying to find newest PNG.")
                                    matching_files = [os.path.join(output_folder, f) for f in os.listdir(output_folder) if f.lower().endswith('.png')]
                                    matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                                    if not matching_files:
                                        logger.error("Export failed - no image found after export attempt.")
                                        response_data = {"status": "error", "message": "Export failed - no image found after export."}
                                        self._set_response(status_code=500)
                                        self.wfile.write(json.dumps(response_data).encode('utf-8'))
                                        return
                                    else:
                                        exported_file_path_actual = matching_files[0]
                                        logger.info("Found newest exported file (fallback): %s", exported_file_path_actual)
                                else:
                                     logger.info("Exported file name from GetSavedFileName: %s", exported_file_path_actual)

                                if os.path.exists(exported_file_path_actual):
                                    with open(exported_file_path_actual, 'rb') as img_file:
                                        img_data_bytes = img_file.read()
                                   
                                    encoded_base64_image_data = base64.b64encode(img_data_bytes).decode('utf-8')
                                    content_type_str = "image/png"

                                    try:
                                        os.remove(exported_file_path_actual)
                                        logger.info("Removed temporary exported file: %s", exported_file_path_actual)
                                    except Exception as e_remove:
                                        logger.warning("Could not remove temporary exported file {}: {}".format(exported_file_path_actual, e_remove))

                                    response_data = {
                                        "status": "success", 
                                        "data": {
                                            "image_data": encoded_base64_image_data,
                                            "content_type": content_type_str,
                                            "view_name": view_name_to_export,
                                            "message": "View exported successfully."
                                        }
                                    }
                                    self._set_response()
                                else: # File still not found
                                    logger.error("Exported file path determined as '%s' but file does not exist.", exported_file_path_actual)
                                    response_data = {"status": "error", "message": "Exported image file not found at expected path after export."}
                                    self._set_response(status_code=500)
                                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                                    return

                    except Exception as view_export_e:
                        logger.error("Error during view export process for '{}': {}".format(view_name_to_export, view_export_e), exc_info=True)
                        response_data = {"status": "error", "message": "Error during view export: {}".format(view_export_e)}
                        self._set_response(status_code=500)
                        self.wfile.write(json.dumps(response_data).encode('utf-8'))
                        return
            else:
                response_data = {"status": "error", "message": "Unknown command: {}".format(command_name)}
                self._set_response(status_code=400)
            # --- End Command Processing ---

        except Exception as e:
            logger.error("Error processing POST request: %s", e, exc_info=True)
            response_data = {"status": "error", "message": "Fatal error processing request: {}".format(e)}
            self._set_response(status_code=500)
        
        logger.debug("Preparing to send response: %s", response_data)
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        logger.info("Response sent for command: '%s'", command_name)

# Global variable to hold the server thread instance
SERVER_THREAD = None
HTTPD_INSTANCE = None # To allow stopping it

def configure_listener_logging():
    global logger
    if not logger.handlers: # Configure only if no handlers exist
        try:
            user_documents = os.path.expanduser("~/Documents")
            log_dir_path = os.path.join(user_documents, 'RevitMCP', 'listener_logs')

            if not os.path.exists(log_dir_path):
                os.makedirs(log_dir_path)
            
            log_file_path = os.path.join(log_dir_path, 'revit_listener.log')
            logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(log_file_path, mode='a')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            logger.info("Revit Listener logging configured: %s", log_file_path)

        except Exception as log_e:
            print("CRITICAL: Failed to configure file logging for Revit Listener: {}".format(log_e))


def start_revit_listener_server():
    """Starts the HTTP server in a separate thread."""
    global SERVER_THREAD, HTTPD_INSTANCE, logger
    
    configure_listener_logging() # Ensure logger is configured

    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        logger.info("Listener server is already running.")
        print("RevitMCP Listener is already running.") # Feedback for pyRevit console
        return

    def target():
        global HTTPD_INSTANCE
        try:
            # Attempt to start the server
            # It's important that this print statement, if it's the cause, is also handled
            # or moved if it's not essential for the immediate startup logic.
            logger.info("Listener starting on http://{}:{}...".format(HOST_NAME, PORT_NUMBER))
            
            server_address = (HOST_NAME, PORT_NUMBER)
            HTTPD_INSTANCE = HTTPServer(server_address, RevitListenerHandler)
            
            # This print statement is the one identified in the traceback
            try:
                print("RevitMCP Listener starting on http://{}:{}.".format(HOST_NAME, PORT_NUMBER))
            except SystemError as se_print:
                logger.warning("Console print failed for listener start message (SystemError): %s. Attempting to continue server.", se_print)
            
            HTTPD_INSTANCE.serve_forever()

        except SystemError as se: # Catch the specific STA error
            logger.error("Could not start or run listener server (SystemError): %s", se, exc_info=True)
            # Optionally, re-raise if you want the thread to terminate and signal failure
            # raise
        except Exception as e:
            logger.error("Could not start or run listener server (General Exception): %s", e, exc_info=True)
            # Optionally, re-raise
            # raise
        finally:
            logger.info("Listener server thread finished.")
            try:
                print("RevitMCP Listener server thread finished.")
            except SystemError:
                logger.warning("Console print failed for listener thread finished message (SystemError).")

    SERVER_THREAD = threading.Thread(target=target)
    SERVER_THREAD.daemon = True  # Allow main program to exit even if thread is running
    SERVER_THREAD.start()
    logger.info("Listener server thread started.")

def stop_revit_listener_server():
    """Stops the HTTP server if it's running."""
    global SERVER_THREAD, HTTPD_INSTANCE, logger
    logger.info("Attempting to stop listener server...")
    print("Attempting to stop RevitMCP Listener...")
    if HTTPD_INSTANCE:
        try:
            HTTPD_INSTANCE.shutdown()
            HTTPD_INSTANCE.server_close()
            HTTPD_INSTANCE = None
            logger.info("HTTPD_INSTANCE shutdown and closed.")
            print("RevitMCP Listener instance shut down.")
        except Exception as e_shutdown:
            logger.error("Error during HTTPD_INSTANCE shutdown: %s", e_shutdown, exc_info=True)
            print("Error shutting down Listener instance: {}".format(e_shutdown))
    else:
        logger.info("HTTPD_INSTANCE was not found (already None).")
        print("RevitMCP Listener instance not found (already None).")

    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        SERVER_THREAD.join(timeout=5.0) 
        if SERVER_THREAD.is_alive():
            logger.warning("Listener server thread did not stop in time.")
            print("WARNING: RevitMCP Listener thread did not stop in time.")
        else:
            logger.info("Listener server thread stopped.")
            print("RevitMCP Listener thread stopped.")
        SERVER_THREAD = None
    else:
        logger.info("Listener server thread was not running or already None.")
        print("RevitMCP Listener thread not running or already None.")
    logger.info("stop_revit_listener_server completed.")

def main(): # Kept for potential direct testing, but not primary use in pyRevit
    configure_listener_logging() # Configure logging for direct test mode too
    logger.info("Starting listener via __main__ (direct test mode)...")
    start_revit_listener_server()
    print("Listener started from __main__. Press Ctrl+C to stop.")
    if __name__ == "__main__":
        try:
            while True:
                import time
                time.sleep(1) # Keep main thread alive
        except KeyboardInterrupt:
            logger.info("Ctrl+C received in __main__. Stopping listener server...")
            print("Ctrl+C received. Stopping listener...")
        finally:
            stop_revit_listener_server()
            logger.info("Listener server stopped from __main__.")
            print("Listener stopped from __main__.")

# This main guard is for direct execution (e.g. ipy.exe listener.py)
# For pyRevit, the button scripts will import this module and call 
# start_revit_listener_server() or stop_revit_listener_server() directly.
if __name__ == "__main__":
    main() 