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

try:
    # For Python 2.7 (IronPython)
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    import json # Standard library
except ImportError:
    # Fallback for Python 3 (for local testing if needed, though target is IronPython)
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import json

import threading # Added for running server in a separate thread

HOST_NAME = 'localhost'
PORT_NUMBER = 8001 # As specified in architecture.md

class RevitListenerHandler(BaseHTTPRequestHandler):
    def _set_response(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        response_data = {}
        try:
            # IronPython json might need explicit string decode from byte array
            command_data = json.loads(post_data.decode('utf-8') if hasattr(post_data, 'decode') else post_data)
            print("Received command: {}".format(command_data))

            # --- Command Processing Logic (Placeholder) ---
            if command_data.get("command") == "get_document_title":
                # In a real scenario, you'd call Revit API here
                # doc_title = __revit__.Application.ActiveUIDocument.Document.Title # Example
                doc_title = "DummyRevitProject.rvt" # Placeholder
                response_data = {"status": "success", "data": doc_title}
                self._set_response()
            elif command_data.get("command") == "get_selected_element_ids":
                # element_ids = [el.Id.IntegerValue for el in __revit__.ActiveUIDocument.Selection.GetElementIds()] # Example
                element_ids = [123, 456] # Placeholder
                response_data = {"status": "success", "data": element_ids}
                self._set_response()
            else:
                response_data = {"status": "error", "message": "Unknown command"}
                self._set_response(status_code=400)
            # --- End Command Processing ---

        except Exception as e:
            error_message = "Error processing request: {}".format(e)
            print(error_message)
            response_data = {"status": "error", "message": error_message}
            self._set_response(status_code=500)
        
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

# Global variable to hold the server thread instance
SERVER_THREAD = None
HTTPD_INSTANCE = None # To allow stopping it

def start_revit_listener_server():
    """Starts the HTTP server in a separate thread."""
    global SERVER_THREAD, HTTPD_INSTANCE
    
    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        print("Revit Listener server is already running.")
        # Optionally, use pyrevit.forms to alert user if in pyRevit context
        return

    def target():
        global HTTPD_INSTANCE
        HTTPD_INSTANCE = HTTPServer((HOST_NAME, PORT_NUMBER), RevitListenerHandler)
        print("RevitMCP Revit Listener starting on http://{0}:{1} in a new thread...".format(HOST_NAME, PORT_NUMBER))
        HTTPD_INSTANCE.serve_forever()
        print("RevitMCP Revit Listener thread finished.") # Should only print if serve_forever stops

    SERVER_THREAD = threading.Thread(target=target)
    SERVER_THREAD.daemon = True  # Allow main program to exit even if thread is running
    SERVER_THREAD.start()
    print("Revit Listener server thread started.")

def stop_revit_listener_server():
    """Stops the HTTP server if it's running."""
    global SERVER_THREAD, HTTPD_INSTANCE
    if HTTPD_INSTANCE:
        print("Attempting to stop Revit Listener server...")
        HTTPD_INSTANCE.shutdown() # Signal serve_forever to stop
        HTTPD_INSTANCE.server_close() # Close the server socket
        HTTPD_INSTANCE = None
        print("Revit Listener server shutdown initiated.")
    else:
        print("Revit Listener server is not currently running or instance not found.")

    if SERVER_THREAD is not None and SERVER_THREAD.is_alive():
        SERVER_THREAD.join(timeout=5.0) # Wait for the thread to finish
        if SERVER_THREAD.is_alive():
            print("Revit Listener server thread did not stop in time.")
        else:
            print("Revit Listener server thread stopped.")
        SERVER_THREAD = None
    else:
        print("Revit Listener server thread is not running.")

def main(): # Kept for potential direct testing, but not primary use in pyRevit
    print("Initializing RevitMCP Revit Listener (direct test mode)...")
    start_revit_listener_server()
    print("Revit Listener main() function called. Server should be running in a background thread.")
    print("To stop the server when testing directly, interrupt (Ctrl+C).")
    if __name__ == "__main__":
        try:
            while True:
                # Keep main thread alive for Ctrl+C
                # In a real pyRevit context, the button script would exit, thread continues
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("Keyboard interrupt received. Stopping listener server...")
        finally:
            stop_revit_listener_server()

# This main guard is for direct execution (e.g. ipy.exe listener.py)
# For pyRevit, the button scripts will import this module and call 
# start_revit_listener_server() or stop_revit_listener_server() directly.
if __name__ == "__main__":
    main() 