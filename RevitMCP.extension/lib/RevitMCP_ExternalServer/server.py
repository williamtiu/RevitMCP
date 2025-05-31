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
from flask import Flask, request, jsonify, render_template
import requests
from flask_cors import CORS

# LLM Libraries
import openai
import anthropic
import google.generativeai as genai
from google.generativeai import types as google_types

# MCP SDK Import
from mcp.server.fastmcp import FastMCP

# --- Centralized Logging Configuration ---
USER_DOCUMENTS = os.path.expanduser("~/Documents")
LOG_BASE_DIR = os.path.join(USER_DOCUMENTS, 'RevitMCP', 'server_logs')
if not os.path.exists(LOG_BASE_DIR):
    os.makedirs(LOG_BASE_DIR)

STARTUP_LOG_FILE = os.path.join(LOG_BASE_DIR, 'server_startup_error.log')
APP_LOG_FILE = os.path.join(LOG_BASE_DIR, 'server_app.log')

startup_logger = logging.getLogger('RevitMCPServerStartup')
startup_logger.setLevel(logging.DEBUG)
if os.path.exists(STARTUP_LOG_FILE):
    try:
        os.remove(STARTUP_LOG_FILE)
    except Exception:
        pass
startup_file_handler = logging.FileHandler(STARTUP_LOG_FILE)
startup_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
startup_logger.addHandler(startup_file_handler)
startup_logger.info("--- Server script attempting to start ---")

def configure_flask_logger(app_instance, debug_mode):
    file_handler = logging.FileHandler(APP_LOG_FILE, mode='a')
    file_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    for handler in list(app_instance.logger.handlers):
        app_instance.logger.removeHandler(handler)
    app_instance.logger.addHandler(file_handler)
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
    print("--- RevitMCP External Server script starting (Python print) ---")

    app = Flask(__name__, template_folder='templates', static_folder='static')
    CORS(app)
    
    DEBUG_MODE = os.environ.get('FLASK_DEBUG_MODE', 'True').lower() == 'true'
    PORT = int(os.environ.get('FLASK_PORT', 8000))
    
    configure_flask_logger(app, DEBUG_MODE)
    app.logger.info("Flask app initialized. Debug mode: %s. Port: %s.", DEBUG_MODE, PORT)
    print(f"--- Flask DEBUG_MODE is set to: {DEBUG_MODE} (from print) ---")

    # --- MCP Server Instance ---
    mcp_server = FastMCP("RevitMCPServer")
    app.logger.info("FastMCP server instance created: %s", mcp_server.name)

    # --- Revit MCP API Communication ---
    # Directly set the API base URL, bypassing discovery, based on the hypothesis
    # that 'revit-mcp-v1' is a top-level API registered with pyRevit Routes.
    REVIT_MCP_API_BASE_URL = "http://localhost:48884/revit-mcp-v1" # Corrected port to 48884 based on user confirmation
    # PYREVIT_CORE_API_URL = "http://localhost:48887/pyrevit-core/apis" # No longer needed for discovery
    # TARGET_MCP_API_NAME = 'revit-mcp-v1' # No longer needed for discovery

    # def discover_revit_mcp_api_url(logger_instance, core_api_url_param, target_api_name_param):
    #     """Attempts to discover the base URL of the RevitMCP API via pyRevit Core API."""
    #     global REVIT_MCP_API_BASE_URL
    #     if REVIT_MCP_API_BASE_URL:
    #         return True
    #     logger_instance.info(f"Attempting to discover RevitMCP API ({target_api_name_param}) via {core_api_url_param}")
    #     try:
    #         response = requests.get(core_api_url_param, timeout=10)
    #         response.raise_for_status()
    #         core_apis = response.json()
    #         if isinstance(core_apis, list):
    #             for api_info in core_apis:
    #                 if isinstance(api_info, dict) and api_info.get('name') == target_api_name_param:
    #                     core_api_base_parts = core_api_url_param.split('/')
    #                     if len(core_api_base_parts) >= 3:
    #                         pyrevit_server_base = f"{core_api_base_parts[0]}//{core_api_base_parts[2]}"
    #                         REVIT_MCP_API_BASE_URL = f"{pyrevit_server_base}/{target_api_name_param}"
    #                         logger_instance.info(f"Successfully discovered RevitMCP API URL: {REVIT_MCP_API_BASE_URL}")
    #                         return True
    #                     else:
    #                         logger_instance.error(f"Could not parse pyRevit server base from {core_api_url_param}")
    #                         return False
    #             logger_instance.warning(f"RevitMCP API '{target_api_name_param}' not found in pyRevit Core API list.")
    #         else:
    #             logger_instance.warning(f"pyRevit Core API response was not a list as expected. Response: {core_apis}")
    #         return False
    #     except requests.exceptions.RequestException as e_req:
    #         status_code_info = ""
    #         response_text_info = ""
    #         if hasattr(e_req, 'response') and e_req.response is not None:
    #             status_code_info = f" (Status code: {e_req.response.status_code})"
    #             try:
    #                 response_text_info = f" Response text: {e_req.response.text[:500]}" # Log first 500 chars
    #             except Exception as e_resp_text:
    #                 response_text_info = f" Error reading response text: {e_resp_text}"
    #         logger_instance.error(f"Error discovering RevitMCP API URL from {core_api_url_param}: {e_req}{status_code_info}.{response_text_info}")
    #         return False
    #     except Exception as e_disc:
    #         logger_instance.error(f"Unexpected error during RevitMCP API URL discovery: {e_disc}", exc_info=True)
    #         return False
    # --- End Revit MCP API Communication ---

    # --- Tool Name Constants (used for REVIT_TOOLS_SPEC and dispatch) ---
    REVIT_INFO_TOOL_NAME = "get_revit_project_info"
    GET_REVIT_VIEW_TOOL_NAME = "get_revit_view" # Corresponds to "export_revit_view" listener command
    SELECT_ELEMENTS_TOOL_NAME = "select_elements_by_id"
    SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME = "select_elements_by_category"

    # --- Helper function to call Revit Listener (remains mostly the same) ---
    # This function is now central for all Revit interactions triggered by MCP tools.
    def call_revit_listener(command_path: str, method: str = 'POST', payload_data: dict = None):
        global REVIT_MCP_API_BASE_URL
        logger_instance = app.logger # Correctly uses app.logger for this function scope

        # Try to discover the API URL if not already set (Now REVIT_MCP_API_BASE_URL is set directly)
        if REVIT_MCP_API_BASE_URL is None: # This condition should ideally not be met anymore
            logger_instance.error("Revit MCP API base URL is not set. This should not happen with direct configuration.")
            # Fallback or error if direct setting failed or was reverted, though discover_revit_mcp_api_url is now commented.
            # if not discover_revit_mcp_api_url(logger_instance, PYREVIT_CORE_API_URL, TARGET_MCP_API_NAME): # This call would fail as func is commented
            #    logger_instance.error("Failed to discover Revit MCP API URL. Listener might not be running or accessible.")
            return {"status": "error", "message": "Could not connect to Revit Listener: API URL not configured."}
            
        logger_instance.info(f"Using pre-configured Revit MCP API base URL: {REVIT_MCP_API_BASE_URL}")

        full_url = REVIT_MCP_API_BASE_URL.rstrip('/') + "/" + command_path.lstrip('/')
        logger_instance.debug(f"Calling Revit MCP API: {method} {full_url} with payload: {payload_data}")

        try:
            if method.upper() == 'POST':
                listener_response = requests.post(
                    full_url, 
                    json=payload_data, 
                    headers={'Content-Type': 'application/json'},
                    timeout=60 
                )
            elif method.upper() == 'GET':
                listener_response = requests.get(
                    full_url, 
                    params=payload_data, # GET requests use params for payload
                    timeout=60
                )
            else:
                logger_instance.error(f"Unsupported HTTP method: {method} for call_revit_listener")
                return {"status": "error", "message": f"Unsupported HTTP method: {method}"}

            listener_response.raise_for_status()
            response_json = listener_response.json()
            logger_instance.info(f"Revit MCP API success for {command_path}: {response_json}")
            return response_json
        except requests.exceptions.ConnectionError:
            msg = f"Could not connect to the Revit MCP API at {full_url} for command {command_path}."
            logger_instance.error(msg)
            # Reset base URL if connection fails, so it attempts rediscovery next time
            # global REVIT_MCP_API_BASE_URL # This was correctly commented out/removed in previous steps
            return {"status": "error", "message": msg}
        except requests.exceptions.Timeout:
            msg = f"Request to Revit MCP API at {full_url} for command {command_path} timed out."
            logger_instance.error(msg)
            return {"status": "error", "message": msg}
        except requests.exceptions.RequestException as e_req:
            msg_prefix = f"Error communicating with Revit MCP API at {full_url} for {command_path}"
            if hasattr(e_req, 'response') and e_req.response is not None:
                status_code = e_req.response.status_code
                try:
                    listener_err_data = e_req.response.json()
                    full_msg = f"{msg_prefix}: HTTP {status_code}. API Response: {listener_err_data.get('message', listener_err_data.get('error', 'Unknown API error'))}"
                    logger_instance.error(full_msg, exc_info=False) # No need for exc_info if we have API message
                    return {"status": "error", "message": full_msg, "details": listener_err_data}
                except ValueError:
                    full_msg = f"{msg_prefix}: HTTP {status_code}. Response: {e_req.response.text[:200]}"
                    logger_instance.error(full_msg, exc_info=True)
                    return {"status": "error", "message": full_msg}
            else:
                logger_instance.error(f"{msg_prefix}: {e_req}", exc_info=True)
                return {"status": "error", "message": f"{msg_prefix}: {e_req}"}
        except Exception as e_gen:
            logger_instance.error(f"Unexpected error in call_revit_listener for {command_path} at {full_url}: {e_gen}", exc_info=True)
            return {"status": "error", "message": f"Unexpected error processing API response for {command_path}."}

    # --- MCP Tool Definitions using @mcp_server.tool() ---
    @mcp_server.tool(name=REVIT_INFO_TOOL_NAME) # Name must match what LLM will use
    def get_revit_project_info_mcp_tool() -> dict:
        """Retrieves detailed information about the currently open Revit project."""
        app.logger.info(f"MCP Tool executed: {REVIT_INFO_TOOL_NAME}")
        return call_revit_listener(command_path='/project_info', method='GET')

    @mcp_server.tool(name=GET_REVIT_VIEW_TOOL_NAME)
    def get_revit_view_mcp_tool(view_name: str) -> dict:
        """Retrieves and displays a specific view from the current Revit project as an image."""
        app.logger.info(f"MCP Tool executed: {GET_REVIT_VIEW_TOOL_NAME} with view_name: {view_name}")
        return call_revit_listener(command_path='/export_revit_view', method='POST', payload_data={"view_name": view_name})

    @mcp_server.tool(name=SELECT_ELEMENTS_TOOL_NAME)
    def select_elements_by_id_mcp_tool(element_ids: list[str]) -> dict:
        """Selects one or more elements in Revit using their Element IDs."""
        app.logger.info(f"MCP Tool executed: {SELECT_ELEMENTS_TOOL_NAME} with element_ids: {element_ids}")
        
        # Ensure element_ids is a list, even if a single string ID is passed by the LLM
        if isinstance(element_ids, str):
            app.logger.warning(f"select_elements_by_id_mcp_tool: element_ids was a string ('{element_ids}'), converting to list.")
            processed_element_ids = [element_ids]
        elif isinstance(element_ids, list) and all(isinstance(eid, str) for eid in element_ids):
            processed_element_ids = element_ids
        elif isinstance(element_ids, list): # List contains non-strings, attempt to convert or log error
            app.logger.warning(f"select_elements_by_id_mcp_tool: element_ids list contained non-string items: {element_ids}. Attempting to convert all to strings.")
            try:
                processed_element_ids = [str(eid) for eid in element_ids]
            except Exception as e_conv:
                app.logger.error(f"select_elements_by_id_mcp_tool: Failed to convert all items in element_ids to string: {e_conv}")
                return {"status": "error", "message": f"Invalid format for element_ids. All IDs must be strings. Received: {element_ids}"}
        else:
            app.logger.error(f"select_elements_by_id_mcp_tool: element_ids is not a string or a list of strings. Received type: {type(element_ids)}, value: {element_ids}")
            return {"status": "error", "message": f"Invalid input type for element_ids. Expected string or list of strings. Received: {type(element_ids)}"}

        return call_revit_listener(command_path='/select_elements_by_id', method='POST', payload_data={"element_ids": processed_element_ids})
    
    @mcp_server.tool(name=SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME)
    def select_elements_by_category_mcp_tool(category_name: str) -> dict:
        """Selects all elements in the Revit model belonging to the specified category."""
        app.logger.info(f"MCP Tool executed: {SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME} with category_name: {category_name}")
        return call_revit_listener(command_path='/select_elements_by_category', method='POST', payload_data={"category_name": category_name})

    app.logger.info("MCP tools defined and decorated.")

    # --- LLM Tool Specifications (Manual for now, for existing LLM API calls) ---
    # These definitions tell the LLMs (OpenAI, Anthropic, Google) about the tools.
    # The 'name' in these specs MUST match the 'name' in @mcp_server.tool() and the constants.
    REVIT_INFO_TOOL_DESCRIPTION_FOR_LLM = "Retrieves detailed information about the currently open Revit project, such as project name, file path, Revit version, Revit build number, and active document title."
    GET_REVIT_VIEW_TOOL_DESCRIPTION_FOR_LLM = "Retrieves and displays a specific view from the current Revit project as an image. Use this if the user asks to see, show, or get a particular Revit view by its name."
    GET_REVIT_VIEW_TOOL_PARAMETERS_FOR_LLM = {
        "type": "object", "properties": {"view_name": {"type": "string", "description": "The exact name of the Revit view to retrieve and display."}}, "required": ["view_name"]
    }
    SELECT_ELEMENTS_TOOL_DESCRIPTION_FOR_LLM = "Selects one or more elements in the current Revit model using their Element IDs. Use this if the user explicitly asks to select elements and provides their IDs, or if a previous tool has returned a list of IDs to be selected."
    SELECT_ELEMENTS_TOOL_PARAMETERS_FOR_LLM = {
        "type": "object", "properties": {"element_ids": {"type": "array", "items": {"type": "string"}, "description": "An array of Element IDs (as strings) of the Revit elements to be selected."}}, "required": ["element_ids"]
    }

    SELECT_ELEMENTS_BY_CATEGORY_TOOL_DESCRIPTION_FOR_LLM = "Selects all elements in the current Revit model that belong to the specified category name (e.g., 'Windows', 'Doors', 'Walls')."
    SELECT_ELEMENTS_BY_CATEGORY_TOOL_PARAMETERS_FOR_LLM = {
        "type": "object", "properties": {"category_name": {"type": "string", "description": "The name of the Revit category to select elements from (e.g., 'Walls', 'Doors', 'Windows')."}}, "required": ["category_name"]
    }

    REVIT_TOOLS_SPEC_FOR_LLMS = {
        "openai": [
            {"type": "function", "function": {"name": REVIT_INFO_TOOL_NAME, "description": REVIT_INFO_TOOL_DESCRIPTION_FOR_LLM, "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": GET_REVIT_VIEW_TOOL_NAME, "description": GET_REVIT_VIEW_TOOL_DESCRIPTION_FOR_LLM, "parameters": GET_REVIT_VIEW_TOOL_PARAMETERS_FOR_LLM}},
            {"type": "function", "function": {"name": SELECT_ELEMENTS_TOOL_NAME, "description": SELECT_ELEMENTS_TOOL_DESCRIPTION_FOR_LLM, "parameters": SELECT_ELEMENTS_TOOL_PARAMETERS_FOR_LLM}},
            {"type": "function", "function": {"name": SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME, "description": SELECT_ELEMENTS_BY_CATEGORY_TOOL_DESCRIPTION_FOR_LLM, "parameters": SELECT_ELEMENTS_BY_CATEGORY_TOOL_PARAMETERS_FOR_LLM}},
        ],
        "anthropic": [
            {"name": REVIT_INFO_TOOL_NAME, "description": REVIT_INFO_TOOL_DESCRIPTION_FOR_LLM, "input_schema": {"type": "object", "properties": {}}},
            {"name": GET_REVIT_VIEW_TOOL_NAME, "description": GET_REVIT_VIEW_TOOL_DESCRIPTION_FOR_LLM, "input_schema": GET_REVIT_VIEW_TOOL_PARAMETERS_FOR_LLM},
            {"name": SELECT_ELEMENTS_TOOL_NAME, "description": SELECT_ELEMENTS_TOOL_DESCRIPTION_FOR_LLM, "input_schema": SELECT_ELEMENTS_TOOL_PARAMETERS_FOR_LLM},
            {"name": SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME, "description": SELECT_ELEMENTS_BY_CATEGORY_TOOL_DESCRIPTION_FOR_LLM, "input_schema": SELECT_ELEMENTS_BY_CATEGORY_TOOL_PARAMETERS_FOR_LLM},
        ],
        "google": [
            google_types.Tool(function_declarations=[
                google_types.FunctionDeclaration(name=REVIT_INFO_TOOL_NAME, description=REVIT_INFO_TOOL_DESCRIPTION_FOR_LLM, parameters={"type": "object", "properties": {}}),
                google_types.FunctionDeclaration(name=GET_REVIT_VIEW_TOOL_NAME, description=GET_REVIT_VIEW_TOOL_DESCRIPTION_FOR_LLM, parameters=GET_REVIT_VIEW_TOOL_PARAMETERS_FOR_LLM),
                google_types.FunctionDeclaration(name=SELECT_ELEMENTS_TOOL_NAME, description=SELECT_ELEMENTS_TOOL_DESCRIPTION_FOR_LLM, parameters=SELECT_ELEMENTS_TOOL_PARAMETERS_FOR_LLM),
                google_types.FunctionDeclaration(name=SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME, description=SELECT_ELEMENTS_BY_CATEGORY_TOOL_DESCRIPTION_FOR_LLM, parameters=SELECT_ELEMENTS_BY_CATEGORY_TOOL_PARAMETERS_FOR_LLM),
            ])
        ]
    }
    app.logger.info("Manual tool specs for LLMs defined.")

    ANTHROPIC_MODEL_ID_MAP = {
        "claude-4-sonnet": "claude-sonnet-4-20250514",    # Updated based on user's table
        "claude-4-opus": "claude-opus-4-20250514",        # Updated based on user's table
        "claude-3-7-sonnet": "claude-3-7-sonnet-20250219",  # Updated based on user's table
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",  # Updated based on user's table
    }
    app.logger.info("Configuration loaded.")

    @app.route('/', methods=['GET'])
    def chat_ui():
        app.logger.info("Serving chat_ui (index.html)")
        return render_template('index.html')

    @app.route('/test_log', methods=['GET'])
    def test_log_route():
        app.logger.info("--- ACCESSED /test_log route successfully (app.logger.info) ---")
        return jsonify({"status": "success", "message": "Test log route accessed. Check server console."}), 200

    @app.route('/chat_api', methods=['POST'])
    def chat_api():
        data = request.json
        conversation_history = data.get('conversation')
        api_key = data.get('apiKey')
        selected_model_ui_name = data.get('model')
        # user_message_content = conversation_history[-1]['content'].strip() # Not directly used anymore for dispatch
        
        final_response_to_frontend = {}
        image_output_for_frontend = None # To store image data if a tool returns it
        model_reply_text = "" # The final text reply from the LLM
        error_message_for_frontend = None

        try:
            if selected_model_ui_name == 'echo_model':
                model_reply_text = f"Echo: {conversation_history[-1]['content']}"
            
            # --- OpenAI Models ---
            elif selected_model_ui_name.startswith('gpt-') or selected_model_ui_name.startswith('o3'):
                client = openai.OpenAI(api_key=api_key)
                messages_for_llm = [{"role": "assistant" if msg['role'] == 'bot' else msg['role'], "content": msg['content']} for msg in conversation_history]
                
                app.logger.debug(f"OpenAI: Sending messages: {messages_for_llm}")
                completion = client.chat.completions.create(model=selected_model_ui_name, messages=messages_for_llm, tools=REVIT_TOOLS_SPEC_FOR_LLMS['openai'], tool_choice="auto")
                response_message = completion.choices[0].message
                tool_calls = response_message.tool_calls

                if tool_calls:
                    messages_for_llm.append(response_message) # Add assistant's turn with tool_calls
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError as e:
                            app.logger.error(f"OpenAI: Failed to parse function arguments for {function_name}: {tool_call.function.arguments}. Error: {e}")
                            tool_response_content = json.dumps({"status": "error", "message": f"Invalid arguments from LLM for tool {function_name}."})
                        else:
                            app.logger.info(f"OpenAI: Tool call requested: {function_name} with args: {function_args}")
                            tool_result_data = {}
                            if function_name == REVIT_INFO_TOOL_NAME:
                                tool_result_data = get_revit_project_info_mcp_tool()
                            elif function_name == GET_REVIT_VIEW_TOOL_NAME:
                                tool_result_data = get_revit_view_mcp_tool(view_name=function_args.get("view_name"))
                            elif function_name == SELECT_ELEMENTS_TOOL_NAME:
                                tool_result_data = select_elements_by_id_mcp_tool(element_ids=function_args.get("element_ids", []))
                            elif function_name == SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME:
                                tool_result_data = select_elements_by_category_mcp_tool(category_name=function_args.get("category_name"))
                            else:
                                app.logger.warning(f"OpenAI: Unknown tool {function_name} called.")
                                tool_result_data = {"status": "error", "message": f"Unknown tool '{function_name}' requested by LLM."}
                            
                            tool_response_content = json.dumps(tool_result_data)
                            if function_name == GET_REVIT_VIEW_TOOL_NAME and tool_result_data.get("status") == "success" and "image_data" in tool_result_data.get("data", {}):
                                image_output_for_frontend = tool_result_data["data"]
                        
                        messages_for_llm.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": tool_response_content})
                    
                    app.logger.debug(f"OpenAI: Resending messages with tool results: {messages_for_llm}")
                    second_completion = client.chat.completions.create(model=selected_model_ui_name, messages=messages_for_llm)
                    model_reply_text = second_completion.choices[0].message.content
                else:
                    model_reply_text = response_message.content

            # --- Anthropic Models ---
            elif selected_model_ui_name.startswith('claude-'):
                client = anthropic.Anthropic(api_key=api_key)
                actual_anthropic_model_id = ANTHROPIC_MODEL_ID_MAP.get(selected_model_ui_name, selected_model_ui_name)
                messages_for_llm = [{"role": "assistant" if msg['role'] == 'bot' else msg['role'], "content": msg['content']} for msg in conversation_history]

                app.logger.debug(f"Anthropic: Sending messages: {messages_for_llm}")
                response = client.messages.create(model=actual_anthropic_model_id, max_tokens=3000, messages=messages_for_llm, tools=REVIT_TOOLS_SPEC_FOR_LLMS['anthropic'], tool_choice={"type": "auto"})
                
                if response.stop_reason == "tool_use":
                    messages_for_llm.append({"role": "assistant", "content": response.content}) # Add assistant's turn
                    tool_results_for_anthropic_user_turn = []

                    for tool_use_block in response.content:
                        if tool_use_block.type == 'tool_use':
                            tool_name = tool_use_block.name
                            tool_input = tool_use_block.input
                            tool_use_id = tool_use_block.id
                            app.logger.info(f"Anthropic: Tool use requested: {tool_name}, Input: {tool_input}, ID: {tool_use_id}")
                            
                            tool_result_data = {}
                            if tool_name == REVIT_INFO_TOOL_NAME:
                                tool_result_data = get_revit_project_info_mcp_tool()
                            elif tool_name == GET_REVIT_VIEW_TOOL_NAME:
                                tool_result_data = get_revit_view_mcp_tool(view_name=tool_input.get("view_name"))
                            elif tool_name == SELECT_ELEMENTS_TOOL_NAME:
                                tool_result_data = select_elements_by_id_mcp_tool(element_ids=tool_input.get("element_ids", []))
                            elif tool_name == SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME:
                                tool_result_data = select_elements_by_category_mcp_tool(category_name=tool_input.get("category_name"))
                            else:
                                app.logger.warning(f"Anthropic: Unknown tool {tool_name} called.")
                                tool_result_data = {"status": "error", "message": f"Unknown tool '{tool_name}' requested by LLM."}

                            tool_results_for_anthropic_user_turn.append({
                                "type": "tool_result", 
                                "tool_use_id": tool_use_id, 
                                "content": json.dumps(tool_result_data) # Anthropic expects content to be string or list of blocks
                            })
                            if tool_name == GET_REVIT_VIEW_TOOL_NAME and tool_result_data.get("status") == "success" and "image_data" in tool_result_data.get("data", {}):
                                image_output_for_frontend = tool_result_data["data"]
                    
                    messages_for_llm.append({"role": "user", "content": tool_results_for_anthropic_user_turn})
                    
                    app.logger.debug(f"Anthropic: Resending messages with tool results: {messages_for_llm}")
                    second_response = client.messages.create(model=actual_anthropic_model_id, max_tokens=3000, messages=messages_for_llm)
                    if second_response.content and second_response.content[0].type == "text":
                        model_reply_text = second_response.content[0].text
                    else: model_reply_text = "Anthropic model responded with non-text content after tool use."
                elif response.content and response.content[0].type == "text":
                    model_reply_text = response.content[0].text
                else: model_reply_text = "Anthropic model returned an unexpected response type."
            
            # --- Google Gemini Models ---
            elif selected_model_ui_name.startswith('gemini-'):
                genai.configure(api_key=api_key)
                # Gemini requires a specific tool configuration for its API
                gemini_tool_config = google_types.ToolConfig(
                    function_calling_config=google_types.FunctionCallingConfig(
                        mode=google_types.FunctionCallingConfig.Mode.AUTO
                    )
                )
                model = genai.GenerativeModel(selected_model_ui_name, tools=REVIT_TOOLS_SPEC_FOR_LLMS['google'], tool_config=gemini_tool_config)
                
                gemini_history_for_chat = []
                for msg in conversation_history:
                    role = 'user' if msg['role'] == 'user' else 'model'
                    gemini_history_for_chat.append({'role': role, 'parts': [google_types.Part(text=msg['content'])]}) # Basic text parts
                
                # The last message is the current user prompt
                current_user_prompt_parts = gemini_history_for_chat.pop()['parts']

                chat_session = model.start_chat(history=gemini_history_for_chat)
                app.logger.debug(f"Google: Sending prompt parts: {current_user_prompt_parts} with history count: {len(chat_session.history)}")

                gemini_response = chat_session.send_message(current_user_prompt_parts)
                
                # Check for function call
                candidate = gemini_response.candidates[0]
                if candidate.content.parts and candidate.content.parts[0].function_call:
                    function_call = candidate.content.parts[0].function_call
                    function_name = function_call.name
                    function_args = dict(function_call.args)
                    app.logger.info(f"Google: Function call requested: {function_name} with args {function_args}")

                    tool_result_data = {}
                    if function_name == REVIT_INFO_TOOL_NAME:
                        tool_result_data = get_revit_project_info_mcp_tool()
                    elif function_name == GET_REVIT_VIEW_TOOL_NAME:
                        tool_result_data = get_revit_view_mcp_tool(view_name=function_args.get("view_name"))
                    elif function_name == SELECT_ELEMENTS_TOOL_NAME:
                        tool_result_data = select_elements_by_id_mcp_tool(element_ids=function_args.get("element_ids", []))
                    elif function_name == SELECT_ELEMENTS_BY_CATEGORY_TOOL_NAME:
                        tool_result_data = select_elements_by_category_mcp_tool(category_name=function_args.get("category_name"))
                    else:
                        app.logger.warning(f"Google: Unknown tool {function_name} called.")
                        tool_result_data = {"status": "error", "message": f"Unknown tool '{function_name}' requested by LLM."}

                    if function_name == GET_REVIT_VIEW_TOOL_NAME and tool_result_data.get("status") == "success" and "image_data" in tool_result_data.get("data", {}):
                        image_output_for_frontend = tool_result_data["data"]

                    function_response_part = google_types.Part(
                        function_response=google_types.FunctionResponse(name=function_name, response=tool_result_data)
                    )
                    app.logger.debug(f"Google: Resending with tool response: {function_response_part}")
                    gemini_response_after_tool = chat_session.send_message(function_response_part)
                    model_reply_text = gemini_response_after_tool.text
                else:
                    model_reply_text = gemini_response.text
            else:
                error_message_for_frontend = f"Model '{selected_model_ui_name}' is not recognized or supported."

        except openai.APIConnectionError as e:
            error_message_for_frontend = f"OpenAI Connection Error: {e}. Please check network or API key."
            app.logger.error(f"OpenAI Connection Error: {e}", exc_info=True)
        except openai.AuthenticationError as e:
            error_message_for_frontend = f"OpenAI Authentication Error: {e}. Invalid API Key?"
            app.logger.error(f"OpenAI Authentication Error: {e}", exc_info=True)
        except openai.RateLimitError as e:
            error_message_for_frontend = f"OpenAI Rate Limit Error: {e}. Please try again later."
            app.logger.error(f"OpenAI Rate Limit Error: {e}", exc_info=True)
        except openai.APIError as e:
            error_message_for_frontend = f"OpenAI API Error: {e} (Status: {e.status_code if hasattr(e, 'status_code') else 'N/A'})."
            app.logger.error(f"OpenAI API Error: {e}", exc_info=True)
        except anthropic.APIConnectionError as e:
            error_message_for_frontend = f"Anthropic Connection Error: {e}. Please check network or API key."
            app.logger.error(f"Anthropic Connection Error: {e}", exc_info=True)
        except anthropic.AuthenticationError as e:
            error_message_for_frontend = f"Anthropic Authentication Error: {e}. Invalid API Key?"
            app.logger.error(f"Anthropic Authentication Error: {e}", exc_info=True)
        except anthropic.RateLimitError as e:
            error_message_for_frontend = f"Anthropic Rate Limit Error: {e}. Please try again later."
            app.logger.error(f"Anthropic Rate Limit Error: {e}", exc_info=True)
        except anthropic.APIError as e: # Catch generic Anthropic API errors
            error_message_for_frontend = f"Anthropic API Error: {e} (Status: {e.status_code if hasattr(e, 'status_code') else 'N/A'})."
            app.logger.error(f"Anthropic API Error: {e}", exc_info=True)
        except Exception as e: # General fallback for other LLM or unexpected errors
            error_message_for_frontend = f"An unexpected error occurred: {str(e)}"
            app.logger.error(f"Chat API error: {type(e).__name__} - {str(e)}", exc_info=True)

        final_response_to_frontend["reply"] = model_reply_text
        if image_output_for_frontend:
            final_response_to_frontend["image_output"] = image_output_for_frontend
        
        if error_message_for_frontend and not model_reply_text:
            return jsonify({"error": error_message_for_frontend}), 500
        elif error_message_for_frontend:
            final_response_to_frontend["error_detail"] = error_message_for_frontend
            return jsonify(final_response_to_frontend) # Include error if model also gave partial reply
        else:
            return jsonify(final_response_to_frontend)

    @app.route('/send_revit_command', methods=['POST'])
    def send_revit_command():
        client_request_data = request.json
        if not client_request_data or "command" not in client_request_data:
            return jsonify({"status": "error", "message": "Invalid request. 'command' is required."}), 400
        revit_command_payload = client_request_data
        actual_revit_listener_url = "http://localhost:8001" 
        app.logger.info(f"External Server (/send_revit_command): Forwarding {revit_command_payload} to {actual_revit_listener_url}")
        try:
            response_from_revit = requests.post(actual_revit_listener_url, json=revit_command_payload, headers={'Content-Type': 'application/json'}, timeout=30)
            response_from_revit.raise_for_status()
            revit_response_data = response_from_revit.json()
            app.logger.info(f"External Server: Response from Revit Listener: {revit_response_data}")
            return jsonify(revit_response_data), response_from_revit.status_code
        except requests.exceptions.ConnectionError as e:
            msg = f"Could not connect to Revit Listener at {actual_revit_listener_url}. Error: {e}"
            app.logger.error(msg)
            return jsonify({"status": "error", "message": msg}), 503
        except requests.exceptions.Timeout as e:
            msg = f"Request to Revit Listener timed out. Error: {e}"
            app.logger.error(msg)
            return jsonify({"status": "error", "message": msg}), 504
        except requests.exceptions.RequestException as e:
            msg = f"Error communicating with Revit Listener. Error: {e}"
            app.logger.error(msg)
            details = "No response details."
            if hasattr(e, 'response') and e.response is not None:
                try: details = e.response.json()
                except ValueError: details = e.response.text
            status = e.response.status_code if hasattr(e, 'response') and e.response is not None else 500
            return jsonify({"status": "error", "message": msg, "details": details}), status
        except Exception as e:
            msg = f"Unexpected error in /send_revit_command. Error: {e}"
            app.logger.error(msg, exc_info=True)
            return jsonify({"status": "error", "message": msg}), 500

    # Add a pause for debugging console window issues
    print("--- server.py script execution reached near end (before __main__ check) ---")
    # input("Press Enter to continue launching Flask server...") # Python 3

    if __name__ == '__main__':
        startup_logger.info(f"--- Starting Flask development server on host 0.0.0.0, port {PORT} ---")
        print(f"--- Debug mode for app.run is: {DEBUG_MODE} ---")
        try:
            app.run(debug=DEBUG_MODE, port=PORT, host='0.0.0.0')
            startup_logger.info("Flask app.run() exited normally.")
        except OSError as e_os:
            startup_logger.error(f"OS Error during server startup (app.run): {e_os}", exc_info=True)
            print(f"OS Error: {e_os}")
        except Exception as e_main_run:
            startup_logger.error(f"Unexpected error during server startup (app.run in __main__): {e_main_run}", exc_info=True)
            print(f"Unexpected error: {e_main_run}")

except Exception as e_global:
    startup_logger.error("!!!!!!!!!! GLOBAL SCRIPT EXECUTION ERROR !!!!!!!!!!", exc_info=True)
    sys.stderr.write(f"GLOBAL SCRIPT ERROR: {e_global}\n{traceback.format_exc()}\n")
    sys.stderr.write(f"Check '{STARTUP_LOG_FILE}' for details.\n")
finally:
    startup_logger.info("--- Server script execution finished or encountered a global error ---")
    # input("Server.py finished or errored. Press Enter to close window...") # Python 3 