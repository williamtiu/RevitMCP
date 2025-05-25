# RevitMCP: This script runs in a standard CPython 3.7+ environment. Modern Python syntax is expected.
"""
External Flask server for RevitMCP.
This server will handle requests from the Revit UI (via a listener)
and can also host a web UI for direct interaction.
"""

import os
import sys # Ensure sys is imported for stdout/stderr redirection if used
import logging
import traceback # For detailed exception logging
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
from flask_cors import CORS

# LLM Libraries - Initialize them if needed, or do it per-request
import openai
import anthropic
import google.generativeai as genai
from google.generativeai import types as google_types # For Tool and FunctionDeclaration

# --- Centralized Logging Configuration ---
USER_DOCUMENTS = os.path.expanduser("~/Documents")
LOG_BASE_DIR = os.path.join(USER_DOCUMENTS, 'RevitMCP', 'server_logs')
if not os.path.exists(LOG_BASE_DIR):
    os.makedirs(LOG_BASE_DIR)

STARTUP_LOG_FILE = os.path.join(LOG_BASE_DIR, 'server_startup_error.log')
APP_LOG_FILE = os.path.join(LOG_BASE_DIR, 'server_app.log')

# Configure a specific logger for startup/global errors
startup_logger = logging.getLogger('RevitMCPServerStartup')
startup_logger.setLevel(logging.DEBUG)
# Clear previous startup log if it exists
if os.path.exists(STARTUP_LOG_FILE):
    try:
        os.remove(STARTUP_LOG_FILE)
    except Exception:
        # If removal fails, just proceed, it will be appended.
        pass
startup_file_handler = logging.FileHandler(STARTUP_LOG_FILE)
startup_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
startup_logger.addHandler(startup_file_handler)
startup_logger.info("--- Server script attempting to start ---")

def configure_flask_logger(app_instance, debug_mode):
    """Configures the Flask app's logger."""
    # File handler for Flask app logs
    file_handler = logging.FileHandler(APP_LOG_FILE, mode='a') # Append mode
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Remove default handlers if any, to avoid duplicate console logs from Flask
    # For example, Flask's default debug handler.
    # This is tricky as app.logger might get handlers from various places.
    # A common approach is to set propagate to False if you fully manage handlers.
    # app_instance.logger.propagate = False 
    
    # Clear existing handlers on app.logger to avoid duplicates if script is re-run in some contexts
    for handler in list(app_instance.logger.handlers):
        app_instance.logger.removeHandler(handler)

    app_instance.logger.addHandler(file_handler)
    
    # Console handler for debug mode
    if debug_mode:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app_instance.logger.addHandler(console_handler)
        app_instance.logger.setLevel(logging.DEBUG)
        app_instance.logger.info("Flask app logger: Configured for DEBUG mode (file and console).")
    else:
        app_instance.logger.setLevel(logging.INFO)
        app_instance.logger.info("Flask app logger: Configured for INFO mode (file only).")
# --- End Centralized Logging Configuration ---

try:
    startup_logger.info("--- RevitMCP External Server script starting (inside main try block) ---")
    print("--- RevitMCP External Server script starting (Python print) ---") # For immediate console feedback

    app = Flask(__name__, template_folder='templates', static_folder='static')
    CORS(app) # Enable CORS for all routes and origins by default
    
    # Configuration
    DEBUG_MODE = os.environ.get('FLASK_DEBUG_MODE', 'True').lower() == 'true'
    PORT = int(os.environ.get('FLASK_PORT', 8000))
    
    # Configure Flask's logger AFTER app initialization and DEBUG_MODE is set
    configure_flask_logger(app, DEBUG_MODE)
    app.logger.info("Flask app initialized. Debug mode: %s. Port: %s.", DEBUG_MODE, PORT)
    print(f"--- Flask DEBUG_MODE is set to: {DEBUG_MODE} (from print) ---")

    # --- Tool Definitions ---
    REVIT_INFO_TOOL_NAME = "get_revit_project_info"
    REVIT_INFO_TOOL_DESCRIPTION = "Retrieves detailed information about the currently open Revit project, such as project name, file path, Revit version, Revit build number, and active document title."

    # New Get Revit View Tool
    GET_REVIT_VIEW_TOOL_NAME = "get_revit_view"
    GET_REVIT_VIEW_TOOL_DESCRIPTION = "Retrieves and displays a specific view from the current Revit project as an image. Use this if the user asks to see, show, or get a particular Revit view by its name."
    GET_REVIT_VIEW_TOOL_PARAMETERS = {
        "type": "object",
        "properties": {
            "view_name": {
                "type": "string",
                "description": "The exact name of the Revit view to retrieve and display."
            }
        },
        "required": ["view_name"]
    }

    REVIT_TOOLS_SPEC = {
        "openai": [
            {
                "type": "function",
                "function": {
                    "name": REVIT_INFO_TOOL_NAME,
                    "description": REVIT_INFO_TOOL_DESCRIPTION,
                    "parameters": {"type": "object", "properties": {}}, 
                },
            },
            {
                "type": "function",
                "function": {
                    "name": GET_REVIT_VIEW_TOOL_NAME,
                    "description": GET_REVIT_VIEW_TOOL_DESCRIPTION,
                    "parameters": GET_REVIT_VIEW_TOOL_PARAMETERS,
                },
            }
        ],
        "anthropic": [
            {
                "name": REVIT_INFO_TOOL_NAME,
                "description": REVIT_INFO_TOOL_DESCRIPTION,
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": GET_REVIT_VIEW_TOOL_NAME,
                "description": GET_REVIT_VIEW_TOOL_DESCRIPTION,
                "input_schema": GET_REVIT_VIEW_TOOL_PARAMETERS,
            }
        ],
        "google": [
            google_types.Tool(
                function_declarations=[
                    google_types.FunctionDeclaration(
                        name=REVIT_INFO_TOOL_NAME,
                        description=REVIT_INFO_TOOL_DESCRIPTION,
                        parameters={"type": "object", "properties": {}}
                    ),
                    google_types.FunctionDeclaration(
                        name=GET_REVIT_VIEW_TOOL_NAME,
                        description=GET_REVIT_VIEW_TOOL_DESCRIPTION,
                        parameters=GET_REVIT_VIEW_TOOL_PARAMETERS
                    )
                ]
            )
        ]
    }
    app.logger.info("Tool specs defined.")

    # Add a mapping for specific model IDs if they differ from the UI selector values
    ANTHROPIC_MODEL_ID_MAP = {
        "claude-4-sonnet": "claude-sonnet-4-20250514", # Corrected based on web search
        "claude-4-opus": "claude-opus-4-20250514",   # Corrected based on web search
        "claude-3-7-sonnet": "claude-3-7-sonnet-20250219", # Verified
        "claude-3-5-sonnet": "claude-3-5-sonnet-20240620", # Verified
        # Add other claude models here if their UI name differs from API ID
    }
    app.logger.info("Configuration loaded.")

    @app.route('/', methods=['GET'])
    def chat_ui():
        app.logger.info("Serving chat_ui (index.html)") # Test Flask logger
        """Serves the main chat UI page."""
        return render_template('index.html')

    # Add a new test route for logging
    @app.route('/test_log', methods=['GET'])
    def test_log_route():
        print("--- PRINT INSIDE /test_log ROUTE ---")
        sys.stdout.write("--- SYS.STDOUT.WRITE INSIDE /test_log ROUTE ---\n")
        sys.stdout.flush()
        sys.stderr.write("--- SYS.STDERR.WRITE INSIDE /test_log ROUTE ---\n")
        sys.stderr.flush()
        app.logger.info("--- ACCESSED /test_log route successfully (app.logger.info) ---")
        return jsonify({"status": "success", "message": "Test log route accessed. Check server console."}), 200

    @app.route('/chat_api', methods=['POST'])
    def chat_api():
        """Handles messages from the chat UI and returns a model response."""
        data = request.json
        conversation_history = data.get('conversation')
        api_key = data.get('apiKey')
        selected_model_ui_name = data.get('model')
        user_message_content = conversation_history[-1]['content'].strip()
        final_response_to_frontend = {}
        image_output_for_frontend = None
        model_reply = ""
        error_message = None

        # Existing call_revit_listener helper function (for POST requests to the listener)
        # This function is now central for all Revit interactions.
        def call_revit_listener(command_name: str, payload_data: dict = None):
            revit_listener_direct_url = "http://localhost:8001"
            payload = {"command": command_name}
            if payload_data:
                 # Ensure payload_data is structured under a 'data' key if listener expects it
                 # Based on project_info_tool, listener might not expect a nested 'data' key for args.
                 # If command expects arguments directly, merge them.
                 # For export_revit_view, we want { "command": "export_revit_view", "view_name": "..." } or similar
                 # Let's assume for now the listener can handle additional keys alongside "command".
                payload.update(payload_data) # e.g. payload becomes {"command": "export_revit_view", "view_name": "L1"}
            
            print(f"External Server: Calling Revit Listener: POST to {revit_listener_direct_url} with payload {payload}")
            try:
                listener_response = requests.post(
                    revit_listener_direct_url, 
                    json=payload, 
                    headers={'Content-Type': 'application/json'},
                    timeout=60 # Increased timeout for potentially long view exports
                )
                listener_response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
                response_json = listener_response.json()

                if response_json.get("status") == "success":
                    print(f"External Server: Revit Listener success for {command_name}: {response_json.get('data', {})}")
                    return response_json
                else:
                    error_detail = response_json.get("message", "Unknown error from Revit Listener")
                    print(f"External Server: Error from Revit Listener ({command_name}): {error_detail}")
                    return {"status": "error", "message": error_detail, "details": response_json.get("details")}
            except requests.exceptions.ConnectionError:
                error_msg_conn = f"External Server: Could not connect to the Revit Listener for command {command_name}. Is it running on {revit_listener_direct_url}?"
                print(error_msg_conn)
                return {"status": "error", "message": error_msg_conn}
            except requests.exceptions.Timeout:
                error_msg_timeout = f"External Server: Request to Revit Listener for command {command_name} timed out."
                print(error_msg_timeout)
                return {"status": "error", "message": error_msg_timeout}
            except requests.exceptions.RequestException as e_req: # Catches HTTPError from raise_for_status too
                error_msg_prefix = f"External Server: Error communicating with Revit Listener for {command_name}"
                
                if hasattr(e_req, 'response') and e_req.response is not None:
                    status_code = e_req.response.status_code
                    reason = e_req.response.reason
                    error_msg_comm = f"{error_msg_prefix}: HTTP {status_code} {reason}"
                    try:
                        listener_json_error = e_req.response.json()
                        error_detail_from_listener = listener_json_error.get("message", f"Listener returned HTTP {status_code} but no specific error message in JSON response.")
                        listener_status = listener_json_error.get("status", "error")
                        listener_details = listener_json_error.get("details")
                        print(f"{error_msg_comm}. Listener detailed error: {error_detail_from_listener}")
                        return {"status": listener_status, "message": f"Listener Error ({status_code}): {error_detail_from_listener}", "details": listener_details}
                    except ValueError: # Response from listener was not JSON
                        error_detail_from_listener_text = e_req.response.text
                        print(f"{error_msg_comm}. Listener response (not JSON): {error_detail_from_listener_text[:300]}") # Log snippet
                        return {"status": "error", "message": f"{error_msg_comm}. Raw response: {error_detail_from_listener_text[:200]}"}
                else:
                    # Original error if no response attribute (e.g. DNS failure, connection refused before response)
                    error_msg_comm = f"{error_msg_prefix}: {str(e_req)}"
                    print(error_msg_comm)
                    return {"status": "error", "message": error_msg_comm}
            except Exception as e_gen: 
                error_msg_gen = f"External Server: An unexpected error occurred processing Revit Listener response for {command_name}: {str(e_gen)}"
                print(error_msg_gen)
                return {"status": "error", "message": error_msg_gen}
        # --- End Helper function ---

        try:
            if selected_model_ui_name == 'echo_model':
                model_reply = f"Echo: {user_message_content}"

            # --- OpenAI Models --- 
            elif selected_model_ui_name.startswith('gpt-') or selected_model_ui_name.startswith('o3'):
                client = openai.OpenAI(api_key=api_key)
                messages_for_openai = []
                for msg in conversation_history: # Simplified history prep
                    messages_for_openai.append({"role": "assistant" if msg['role'] == 'bot' else msg['role'], "content": msg['content']})
                
                completion = client.chat.completions.create(model=selected_model_ui_name, messages=messages_for_openai, tools=REVIT_TOOLS_SPEC['openai'], tool_choice="auto")
                response_message = completion.choices[0].message
                tool_calls = response_message.tool_calls

                if tool_calls:
                    messages_for_openai.append(response_message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        tool_output_data_for_llm = {}

                        if function_name == REVIT_INFO_TOOL_NAME:
                            listener_result = call_revit_listener(REVIT_INFO_TOOL_NAME) # No specific args needed from LLM
                            tool_output_data_for_llm = listener_result.get('data', listener_result) # Pass data or full error
                        elif function_name == GET_REVIT_VIEW_TOOL_NAME:
                            view_name_arg = function_args.get("view_name")
                            if view_name_arg:
                                # Listener expects args directly in payload for this hypothetical command
                                listener_result = call_revit_listener("export_revit_view", {"view_name": view_name_arg})
                                if listener_result.get("status") == "success" and listener_result.get("data", {}).get("image_data"):
                                    image_output_for_frontend = listener_result["data"] # Contains image_data, content_type
                                    tool_output_data_for_llm = {"status": "success", "message": f"Image for '{view_name_arg}' retrieved and will be displayed."}
                                else:
                                    tool_output_data_for_llm = listener_result # Forward error/status to LLM
                            else:
                                tool_output_data_for_llm = {"status": "error", "message": "View name was not provided by the model."}
                        
                        messages_for_openai.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps(tool_output_data_for_llm)})
                    
                    second_completion = client.chat.completions.create(model=selected_model_ui_name, messages=messages_for_openai)
                    model_reply = second_completion.choices[0].message.content
                else:
                    model_reply = response_message.content

            # --- Anthropic Models --- 
            elif selected_model_ui_name.startswith('claude-'):
                client = anthropic.Anthropic(api_key=api_key)
                actual_anthropic_model_id = ANTHROPIC_MODEL_ID_MAP.get(selected_model_ui_name, selected_model_ui_name)
                messages_for_anthropic = [] # Simplified history prep
                for msg in conversation_history: messages_for_anthropic.append({"role": "assistant" if msg['role'] == 'bot' else msg['role'], "content": msg['content']})

                response = client.messages.create(model=actual_anthropic_model_id, max_tokens=2048, messages=messages_for_anthropic, tools=REVIT_TOOLS_SPEC['anthropic'], tool_choice={"type": "auto"})

                if response.stop_reason == "tool_use":
                    messages_for_anthropic.append({"role": "assistant", "content": response.content}) # Append current assistant turn
                    tool_results_for_anthropic = []
                    for tool_use_block in response.content:
                        if tool_use_block.type == 'tool_use':
                            tool_name = tool_use_block.name
                            tool_input = tool_use_block.input
                            tool_id = tool_use_block.id
                            tool_output_data_for_llm = {}

                            if tool_name == REVIT_INFO_TOOL_NAME:
                                listener_result = call_revit_listener(REVIT_INFO_TOOL_NAME)
                                tool_output_data_for_llm = listener_result.get('data', listener_result)
                            elif tool_name == GET_REVIT_VIEW_TOOL_NAME:
                                view_name_arg = tool_input.get("view_name")
                                if view_name_arg:
                                    listener_result = call_revit_listener("export_revit_view", {"view_name": view_name_arg})
                                    if listener_result.get("status") == "success" and listener_result.get("data", {}).get("image_data"):
                                        image_output_for_frontend = listener_result["data"]
                                        tool_output_data_for_llm = {"status": "success", "message": f"Image for '{view_name_arg}' retrieved."}
                                    else:
                                        tool_output_data_for_llm = listener_result
                                else:
                                    tool_output_data_for_llm = {"status": "error", "message": "View name not provided by model."}
                            
                            tool_results_for_anthropic.append({"type": "tool_result", "tool_use_id": tool_id, "content": json.dumps(tool_output_data_for_llm)})
                    
                    messages_for_anthropic.append({"role": "user", "content": tool_results_for_anthropic}) # Follow up with tool results as user role
                    
                    second_response = client.messages.create(model=actual_anthropic_model_id, max_tokens=2048, messages=messages_for_anthropic)
                    if second_response.content and second_response.content[0].type == "text":
                        model_reply = second_response.content[0].text
                    else:
                        model_reply = "Anthropic model responded with non-text content after tool use."
                        print(f"External Server (Anthropic): Unexpected response after tool use: {second_response.content}")

                elif response.content and response.content[0].type == "text":
                    model_reply = response.content[0].text
                else:
                    model_reply = "Anthropic model returned an unexpected response type."
                    print(f"External Server (Anthropic): Unexpected initial response: {response.content}")

            # --- Google Gemini Models --- 
            elif selected_model_ui_name.startswith('gemini-'):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model_ui_name, tools=REVIT_TOOLS_SPEC['google'])
                gemini_history = [] # Simplified history prep
                for msg in conversation_history[:-1]: gemini_history.append({'role': 'user' if msg['role'] == 'user' else 'model', 'parts': [msg['content']]})
                
                chat_session = model.start_chat(history=gemini_history)
                gemini_response = chat_session.send_message(conversation_history[-1]['content'])
                function_call = gemini_response.candidates[0].content.parts[0].function_call if gemini_response.candidates and gemini_response.candidates[0].content.parts and gemini_response.candidates[0].content.parts[0].function_call else None
                
                if function_call:
                    function_name = function_call.name
                    args = {key: value for key, value in function_call.args.items()}
                    tool_output_data_for_llm = None

                    if function_name == REVIT_INFO_TOOL_NAME:
                        listener_result = call_revit_listener(REVIT_INFO_TOOL_NAME)
                        tool_output_data_for_llm = listener_result.get('data', listener_result)
                    elif function_name == GET_REVIT_VIEW_TOOL_NAME:
                        view_name_arg = args.get("view_name")
                        if view_name_arg:
                            listener_result = call_revit_listener("export_revit_view", {"view_name": view_name_arg})
                            if listener_result.get("status") == "success" and listener_result.get("data", {}).get("image_data"):
                                image_output_for_frontend = listener_result["data"]
                                tool_output_data_for_llm = {"status": "success", "message": f"Image for '{view_name_arg}' retrieved."}
                            else:
                                tool_output_data_for_llm = listener_result
                        else:
                            tool_output_data_for_llm = {"status": "error", "message": "View name not provided by Gemini."}

                    gemini_response_after_tool = chat_session.send_message(google_types.Part(function_response=google_types.FunctionResponse(name=function_name, response=tool_output_data_for_llm)))
                    model_reply = gemini_response_after_tool.text
                else:
                    model_reply = gemini_response.text
            else:
                error_message = f"Model '{selected_model_ui_name}' is not recognized or supported."

        except Exception as e:
            # ... (existing detailed error logging and message preparation) ...
            error_message = f"An unexpected error occurred: {str(e)}"
            app.logger.error(f"Chat API error: {type(e).__name__} - {str(e)}", exc_info=True)

        final_response_to_frontend["reply"] = model_reply
        if image_output_for_frontend:
            final_response_to_frontend["image_output"] = image_output_for_frontend
        
        if error_message and not model_reply: # If an error occurred and no model reply was formed
            return jsonify({"error": error_message}), 500
        elif error_message: # If an error occurred but model might have a partial reply
            final_response_to_frontend["error_detail"] = error_message # Add error as extra info
            return jsonify(final_response_to_frontend)
        else:
            return jsonify(final_response_to_frontend)

    @app.route('/send_revit_command', methods=['POST'])
    def send_revit_command():
        client_request_data = request.json
        if not client_request_data or "command" not in client_request_data:
            return jsonify({"status": "error", "message": "Invalid request. 'command' is required."}), 400

        revit_command_payload = client_request_data
        
        # This is the actual URL for the listener itself, not this server's route
        actual_revit_listener_url = "http://localhost:8001" 

        print("External Server (/send_revit_command route): Received request from client: {}".format(client_request_data))
        print("External Server (/send_revit_command route): Forwarding command '{}' to Revit Listener at {}".format(revit_command_payload.get('command'), actual_revit_listener_url))

        try:
            response_from_revit = requests.post(
                actual_revit_listener_url, 
                json=revit_command_payload, 
                headers={'Content-Type': 'application/json'}, 
                timeout=30
            )
            response_from_revit.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            
            revit_response_data = response_from_revit.json()
            print("External Server: Received response from Revit Listener: {}".format(revit_response_data))
            
            return jsonify(revit_response_data), response_from_revit.status_code

        except requests.exceptions.ConnectionError as e:
            error_msg = "External Server: Could not connect to Revit Listener at {}. Is it running? Error: {}".format(actual_revit_listener_url, e)
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 503 # Service Unavailable
        except requests.exceptions.Timeout as e:
            error_msg = "External Server: Request to Revit Listener timed out. Error: {}".format(e)
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 504 # Gateway Timeout
        except requests.exceptions.RequestException as e:
            error_msg = "External Server: Error communicating with Revit Listener. Error: {}".format(e)
            print(error_msg)
            error_details_text = "No response details available."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details_text = e.response.json()
                except ValueError: # Not JSON
                    error_details_text = e.response.text
            return jsonify({"status": "error", "message": error_msg, "details": error_details_text}), \
                   e.response.status_code if hasattr(e, 'response') and e.response is not None else 500
        except Exception as e:
            error_msg = "External Server: An unexpected error occurred. Error: {}".format(e)
            print(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500

    if __name__ == '__main__':
        startup_logger.info(f"--- Starting Flask development server on host 0.0.0.0, port {PORT} ---")
        print(f"--- Debug mode for app.run is: {DEBUG_MODE} ---")
        if not app.logger.handlers and DEBUG_MODE:
            import logging
            # Use sys.stdout for the stream handler
            handler_main_log = logging.StreamHandler(sys.stdout) # Ensure sys is imported
            handler_main_log.setLevel(logging.DEBUG)
            formatter_main_log = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler_main_log.setFormatter(formatter_main_log)
            app.logger.addHandler(handler_main_log)
            app.logger.setLevel(logging.DEBUG)
            app.logger.info("--- Explicitly configured StreamHandler for app.logger in __main__ ---")

        try:
            # Restore reloader for development convenience
            startup_logger.info(f"Attempting to run Flask app with debug={DEBUG_MODE}")
            app.run(debug=DEBUG_MODE, port=PORT, host='0.0.0.0')
            startup_logger.info("Flask app.run() exited normally.") # Will only log if it exits gracefully
        except OSError as e_os:
            import errno
            startup_logger.error(f"OS Error during server startup (app.run): {e_os} (Error No: {e_os.errno})", exc_info=True)
            if e_os.errno == errno.EADDRINUSE or (hasattr(e_os, 'winerror') and e_os.winerror == 10048): # type: ignore
                port_in_use_msg = f"ERROR: Port {PORT} is already in use. Please close the application using this port or change the FLASK_PORT environment variable."
                startup_logger.error(port_in_use_msg)
                print(port_in_use_msg) # Also print to console
            else:
                startup_logger.error(f"Unusual OSError during app.run: {e_os}", exc_info=True)
                print(f"Unusual OSError: {e_os}")
        except Exception as e_main_run:
            startup_logger.error(f"Unexpected error during server startup (app.run in __main__): {e_main_run}", exc_info=True)
            print(f"Unexpected error: {e_main_run}")

except Exception as e_global:
    # Use the startup_logger for errors during initial script setup
    startup_logger.error("!!!!!!!!!! GLOBAL SCRIPT EXECUTION ERROR !!!!!!!!!!")
    startup_logger.error(str(e_global), exc_info=True)
    # Try to print to console as a last resort
    sys.stderr.write(f"GLOBAL SCRIPT ERROR: {e_global}\\n{traceback.format_exc()}\\n")
    sys.stderr.write(f"Check '{STARTUP_LOG_FILE}' for details.\\n")
finally:
    startup_logger.info("--- Server script execution finished or encountered a global error ---")
    # For debugging: input("Script finished or error occurred. Press Enter to exit...") 