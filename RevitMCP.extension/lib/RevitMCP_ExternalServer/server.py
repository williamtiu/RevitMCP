# RevitMCP: This script runs in a standard CPython 3.7+ environment. Modern Python syntax is expected.
"""
External Flask server for RevitMCP.
This server will handle requests from the Revit UI (via a listener)
and can also host a web UI for direct interaction.
"""

print("--- RevitMCP External Server script starting ---") # Early print diagnostic

from flask import Flask, request, jsonify, render_template
import requests # For sending requests to the Revit Listener (if needed in future)
import os
import json # For parsing conversation history if it comes as a string
import sys

# LLM Libraries - Initialize them if needed, or do it per-request
import openai
import anthropic
import google.generativeai as genai
from google.generativeai import types as google_types # For Tool and FunctionDeclaration


app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Tool Definitions ---
REVIT_TOOL_NAME = "get_revit_project_info"
REVIT_TOOL_DESCRIPTION = "Retrieves detailed information about the currently open Revit project, such as project name, file path, Revit version, Revit build number, and active document title."

# Using a dictionary to store provider-specific tool formats
REVIT_TOOLS_SPEC = {
    "openai": [
        {
            "type": "function",
            "function": {
                "name": REVIT_TOOL_NAME,
                "description": REVIT_TOOL_DESCRIPTION,
                "parameters": {"type": "object", "properties": {}}, # No parameters from LLM
            },
        }
    ],
    "anthropic": [
        {
            "name": REVIT_TOOL_NAME,
            "description": REVIT_TOOL_DESCRIPTION,
            "input_schema": {"type": "object", "properties": {}}, # No parameters from LLM
        }
    ],
    "google": [
        google_types.Tool(
            function_declarations=[
                google_types.FunctionDeclaration(
                    name=REVIT_TOOL_NAME,
                    description=REVIT_TOOL_DESCRIPTION,
                    parameters={"type": "object", "properties": {}}, # No parameters from LLM
                )
            ]
        )
    ]
}

# --- End Tool Definitions ---

# Configuration
DEBUG_MODE = os.environ.get('FLASK_DEBUG_MODE', 'True').lower() == 'true'
# Explicitly print DEBUG_MODE status
print(f"--- Flask DEBUG_MODE is set to: {DEBUG_MODE} ---")
PORT = int(os.environ.get('FLASK_PORT', 8000))
REVIT_LISTENER_URL = "http://localhost:8001/send_revit_command" # Corrected: The listener itself is at 8001; send_revit_command is a route on *this* server.
# The actual listener endpoint seems to be just http://localhost:8001 based on listener.py
# The /send_revit_command route on this Flask server is what forwards to the listener.

# Add a mapping for specific model IDs if they differ from the UI selector values
ANTHROPIC_MODEL_ID_MAP = {
    "claude-4-sonnet": "claude-sonnet-4-20250514", # Corrected based on web search
    "claude-4-opus": "claude-opus-4-20250514",   # Corrected based on web search
    "claude-3-7-sonnet": "claude-3-7-sonnet-20250219", # Verified
    "claude-3-5-sonnet": "claude-3-5-sonnet-20240620", # Verified
    # Add other claude models here if their UI name differs from API ID
}

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

    if not conversation_history or not isinstance(conversation_history, list) or not conversation_history[-1].get('content'):
        return jsonify({"error": "No message or invalid conversation history provided"}), 400
    if not selected_model_ui_name:
        return jsonify({"error": "No model selected"}), 400
    
    user_message_content = conversation_history[-1]['content'].strip()

    # --- Helper function to call Revit Listener ---
    def call_revit_listener(command_name: str, payload_data: dict = None):
        revit_listener_direct_url = "http://localhost:8001" 
        payload = {"command": command_name}
        if payload_data:
            payload.update(payload_data)
        
        print(f"External Server: Calling Revit Listener: {command_name} with payload {payload}")
        try:
            listener_response = requests.post(
                revit_listener_direct_url, 
                json=payload, 
                headers={'Content-Type': 'application/json'},
                timeout=20 # Increased timeout slightly
            )
            listener_response.raise_for_status()
            response_json = listener_response.json()

            if response_json.get("status") == "success":
                print(f"External Server: Revit Listener success for {command_name}: {response_json.get('data', {})}")
                return json.dumps(response_json.get("data", {})) # Return data as JSON string
            else:
                error_detail = response_json.get("message", "Unknown error from Revit Listener")
                print(f"External Server: Error from Revit Listener ({command_name}): {error_detail}")
                return json.dumps({"error": error_detail, "details": response_json.get("details")})
        except requests.exceptions.ConnectionError:
            error_msg = f"External Server: Could not connect to the Revit Listener for command {command_name}. Is it running?"
            print(error_msg)
            return json.dumps({"error": error_msg})
        except requests.exceptions.Timeout:
            error_msg = f"External Server: Request to Revit Listener for command {command_name} timed out."
            print(error_msg)
            return json.dumps({"error": error_msg})
        except requests.exceptions.RequestException as e:
            error_msg = f"External Server: Error communicating with Revit Listener for {command_name}: {str(e)}"
            print(error_msg)
            return json.dumps({"error": error_msg})
        except Exception as e: # Catch-all for other errors like JSON parsing
            error_msg = f"External Server: An unexpected error occurred processing Revit Listener response for {command_name}: {str(e)}"
            print(error_msg)
            return json.dumps({"error": error_msg})
    # --- End Helper function ---

    # --- Revit Command Trigger --- 
    if "revit project info" in user_message_content.lower() and selected_model_ui_name == 'echo_model': # Keep for echo model for now
        print(f"User requested Revit project info via keyword for echo_model. Calling listener directly.")
        # Directly call listener and format for echo (or simple direct reply)
        listener_output_str = call_revit_listener(REVIT_TOOL_NAME)
        try:
            listener_output_data = json.loads(listener_output_str)
            if "error" in listener_output_data:
                return jsonify({"reply": f"Error from Revit: {listener_output_data['error']}"})
            
            formatted_info = "Revit Project Information (direct call):\\n"
            for key, value in listener_output_data.items():
                display_key = key.replace('_', ' ').capitalize()
                formatted_info += f"- {display_key}: {value}\\n"
            return jsonify({"reply": formatted_info.strip()})
        except json.JSONDecodeError:
            return jsonify({"reply": f"Revit listener returned non-JSON: {listener_output_str}"})
    # --- End Revit Command Trigger ---

    # Proceed with LLM call if not a Revit command handled above
    user_message = user_message_content # Original variable name for LLM part

    # API key is required for all non-echo models
    if selected_model_ui_name != 'echo_model' and not api_key:
        return jsonify({"error": "API key is required for this model"}), 400

    model_reply = ""
    error_message = None

    try:
        if selected_model_ui_name == 'echo_model':
            model_reply = (
                f"Server echoes: '{user_message}'. "
                f"Model selected: '{selected_model_ui_name}'. "
                f"API Key provided: '{bool(api_key)}'. "
                f"History items: {len(conversation_history)}."
            )
        
        # --- OpenAI Models --- 
        elif selected_model_ui_name.startswith('gpt-') or selected_model_ui_name.startswith('o3'):
            # --- OpenAI Tool Definitions (Localized due to previous edit issues) ---
            REVIT_TOOL_NAME_OPENAI = "get_revit_project_info"
            REVIT_TOOL_DESCRIPTION_OPENAI = "Retrieves detailed information about the currently open Revit project, such as project name, file path, Revit version, Revit build number, and active document title."
            openai_tool_spec = [
                {
                    "type": "function",
                    "function": {
                        "name": REVIT_TOOL_NAME_OPENAI,
                        "description": REVIT_TOOL_DESCRIPTION_OPENAI,
                        "parameters": {"type": "object", "properties": {}}, # No parameters from LLM
                    },
                }
            ]

            # --- Helper function to call Revit Listener (Localized) ---
            def call_revit_listener_for_openai(command_name: str, payload_data: dict = None):
                revit_listener_direct_url = "http://localhost:8001" 
                payload = {"command": command_name}
                if payload_data:
                    payload.update(payload_data)
                
                print(f"External Server (OpenAI): Calling Revit Listener: {command_name} with payload {payload}")
                try:
                    listener_response = requests.post(
                        revit_listener_direct_url, 
                        json=payload, 
                        headers={'Content-Type': 'application/json'},
                        timeout=20
                    )
                    listener_response.raise_for_status()
                    response_json = listener_response.json()

                    if response_json.get("status") == "success":
                        print(f"External Server (OpenAI): Revit Listener success for {command_name}: {response_json.get('data', {})}")
                        return json.dumps(response_json.get("data", {})) 
                    else:
                        error_detail = response_json.get("message", "Unknown error from Revit Listener")
                        print(f"External Server (OpenAI): Error from Revit Listener ({command_name}): {error_detail}")
                        return json.dumps({"error": error_detail, "details": response_json.get("details")})
                except requests.exceptions.RequestException as e:
                    error_msg = f"External Server (OpenAI): Error communicating with Revit Listener for {command_name}: {str(e)}"
                    print(error_msg)
                    return json.dumps({"error": error_msg})
                except Exception as e:
                    error_msg = f"External Server (OpenAI): An unexpected error occurred processing Revit Listener response for {command_name}: {str(e)}"
                    print(error_msg)
                    return json.dumps({"error": error_msg})
            # --- End Helper ---

            client = openai.OpenAI(api_key=api_key)
            messages_for_openai = []
            for msg in conversation_history:
                role = msg.get('role')
                content = msg.get('content')
                if role == 'bot': 
                    role = 'assistant'
                if role and content:
                    messages_for_openai.append({"role": role, "content": content})
            
            if not messages_for_openai:
                 raise ValueError("Message list for OpenAI cannot be empty after filtering.")

            print(f"External Server (OpenAI): Sending to OpenAI: {messages_for_openai}, tools: {openai_tool_spec}")
            completion = client.chat.completions.create(
                model=selected_model_ui_name,
                messages=messages_for_openai,
                tools=openai_tool_spec,
                tool_choice="auto", 
            )
            
            response_message = completion.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                print(f"External Server (OpenAI): Received tool calls: {tool_calls}")
                # For now, we only handle one tool call, the Revit project info.
                # In the future, you might loop through tool_calls if multiple can be returned.
                messages_for_openai.append(response_message) # Add assistant's reply with tool call

                for tool_call in tool_calls:
                    if tool_call.function.name == REVIT_TOOL_NAME_OPENAI:
                        function_args = json.loads(tool_call.function.arguments) # Should be empty for this tool
                        
                        print(f"External Server (OpenAI): Executing tool '{tool_call.function.name}' with args: {function_args}")
                        tool_output_json_str = call_revit_listener_for_openai(REVIT_TOOL_NAME_OPENAI)
                        
                        messages_for_openai.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": REVIT_TOOL_NAME_OPENAI,
                                "content": tool_output_json_str, # Result of the function call
                            }
                        )
                
                print(f"External Server (OpenAI): Sending to OpenAI again with tool results: {messages_for_openai}")
                second_completion = client.chat.completions.create(
                    model=selected_model_ui_name,
                    messages=messages_for_openai
                    # No tools or tool_choice here, we want a text response
                )
                model_reply = second_completion.choices[0].message.content
            else:
                model_reply = response_message.content

        # --- Anthropic Models --- 
        elif selected_model_ui_name.startswith('claude-'):
            client = anthropic.Anthropic(api_key=api_key)
            # Use the mapping to get the correct model ID for the API call
            actual_anthropic_model_id = ANTHROPIC_MODEL_ID_MAP.get(selected_model_ui_name, selected_model_ui_name)
            
            messages_for_anthropic = []
            
            for msg in conversation_history:
                role = msg.get('role')
                content = msg.get('content')
                if role and content:
                    # Ensure content is a list of blocks for Anthropic tool use if needed later
                    # For now, simple text content is fine for user/assistant messages.
                    if role == 'bot':
                        messages_for_anthropic.append({"role": "assistant", "content": content})
                    else: 
                        messages_for_anthropic.append({"role": "user", "content": content})
            
            if not messages_for_anthropic or messages_for_anthropic[-1]["role"] != "user":
                raise ValueError("Anthropic requires the last message to be from the user, or message list is empty.")

            print(f"External Server (Anthropic): Sending to Anthropic with model_id: {actual_anthropic_model_id}")
            
            # Initial call to Anthropic with tools
            response = client.messages.create(
                model=actual_anthropic_model_id,
                max_tokens=1024,
                messages=messages_for_anthropic,
                tools=REVIT_TOOLS_SPEC["anthropic"],
                tool_choice={"type": "auto"} # Let Anthropic decide if to use a tool
            )

            # Check if the model wants to use a tool
            if response.stop_reason == "tool_use":
                tool_use_block = next((block for block in response.content if block.type == "tool_use"), None)
                if tool_use_block and tool_use_block.name == REVIT_TOOL_NAME:
                    tool_input = tool_use_block.input # Should be empty for this tool
                    tool_id = tool_use_block.id
                    print(f"External Server (Anthropic): Received tool use request for '{REVIT_TOOL_NAME}' with ID '{tool_id}' and input: {tool_input}")

                    # Call the Revit listener
                    tool_output_json_str = call_revit_listener(REVIT_TOOL_NAME)
                    
                    # Append the original assistant message (with the tool_use request)
                    messages_for_anthropic.append({"role": "assistant", "content": response.content})
                    
                    # Append the tool result message
                    messages_for_anthropic.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": tool_output_json_str # Content can be a string or list of blocks
                                # Consider sending structured JSON content if tool_output_json_str is complex
                                # For now, sending the JSON string as content.
                            }
                        ]
                    })
                    
                    print(f"External Server (Anthropic): Sending tool results back to Anthropic: {messages_for_anthropic}")
                    # Second call to get the final response from the model
                    second_response = client.messages.create(
                        model=actual_anthropic_model_id,
                        max_tokens=1024,
                        messages=messages_for_anthropic
                        # No tools or tool_choice here, we expect a text response
                    )
                    if second_response.content and second_response.content[0].type == "text":
                        model_reply = second_response.content[0].text
                    else:
                        model_reply = "Anthropic model responded with non-text content after tool use."
                        print(f"External Server (Anthropic): Unexpected response after tool use: {second_response.content}")

                else:
                    model_reply = "Anthropic model requested an unknown or unhandled tool."
                    print(f"External Server (Anthropic): Unhandled tool use block: {tool_use_block}")
            
            elif response.content and response.content[0].type == "text":
                model_reply = response.content[0].text
            else:
                model_reply = "Anthropic model returned an unexpected response type."
                print(f"External Server (Anthropic): Unexpected initial response: {response.content}")

        # --- Google Gemini Models --- (Updated for google-generativeai >= 0.4.0)
        elif selected_model_ui_name.startswith('gemini-'):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(selected_model_ui_name)

            # Gemini expects alternating user/model roles. History needs to be mapped.
            # Content can be a list of parts, but for text, a string is fine.
            gemini_history = [] 
            for msg in conversation_history[:-1]: # Process all but the last user message for history
                role = msg.get('role')
                content = msg.get('content')
                if role == 'user':
                    gemini_history.append({'role': 'user', 'parts': [content]})
                elif role == 'bot' or role == 'assistant': # Gemini uses 'model' for bot replies
                    gemini_history.append({'role': 'model', 'parts': [content]})
            
            chat_session = model.start_chat(history=gemini_history)
            gemini_response = chat_session.send_message(conversation_history[-1]['content']) # Send the latest user message
            model_reply = gemini_response.text

        else:
            error_message = f"Model '{selected_model_ui_name}' is not recognized or supported."
            return jsonify({"error": error_message}), 501 # Not Implemented

    except openai.APIError as e:
        error_message = f"OpenAI API Error: {str(e)}"
    except anthropic.APIError as e:
        error_message = f"Anthropic API Error: {str(e)}"
    except Exception as e: # Catch-all for other errors, including Google specific ones for now
        if hasattr(e, 'message') and e.message: # General exception message
             error_message = f"Error with {selected_model_ui_name}: {e.message}"
        elif hasattr(e, 'args') and e.args: # Some exceptions store messages in args
            error_message = f"Error with {selected_model_ui_name}: {e.args[0] if e.args else str(e)}"
        else:
            error_message = f"An unexpected error occurred with {selected_model_ui_name}: {str(e)}"
        print(f"Error details for {selected_model_ui_name}: {type(e).__name__} - {str(e)}") # Log detailed error

    if error_message:
        return jsonify({"error": error_message}), 500
    else:
        return jsonify({"reply": model_reply})

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
    print(f"--- Starting Flask development server on host 0.0.0.0, port {PORT} ---")
    print(f"--- Debug mode for app.run is: {DEBUG_MODE} ---")
    if not app.logger.handlers and DEBUG_MODE:
        import logging
        # Use sys.stdout for the stream handler
        handler = logging.StreamHandler(sys.stdout) # Ensure sys is imported if not already
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info("--- Explicitly configured StreamHandler for app.logger ---")

    try:
        # Restore reloader for development convenience
        app.run(debug=DEBUG_MODE, port=PORT, host='0.0.0.0')
    except OSError as e:
        # Error codes can vary slightly by OS, but 10048 (Windows) and 98 (Linux/macOS often) are common for "address in use"
        # Python 3.3+ e.errno can be used for cross-platform error numbers like EADDRINUSE
        import errno
        if e.errno == errno.EADDRINUSE or (hasattr(e, 'winerror') and e.winerror == 10048): 
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"!!! CRITICAL ERROR: Port {PORT} is already in use by another process. !!!")
            print(f"!!! Please find and stop the other process, then try starting again.   !!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # Optionally, exit with a specific code if this script were to be monitored
            # sys.exit(1) 
        else:
            print(f"!!! Unusual OSError during server startup: {e} (Error No: {e.errno}) !!!")
    except Exception as e:
        print(f"!!! An unexpected error occurred during server startup: {e} !!!") 