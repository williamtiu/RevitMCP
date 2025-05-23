"""
External Flask server for RevitMCP.
This server will handle requests from the Revit UI (via a listener)
and can also host a web UI for direct interaction.
"""

from flask import Flask, request, jsonify, render_template
import requests # For sending requests to the Revit Listener (if needed in future)
import os
import json # For parsing conversation history if it comes as a string

# LLM Libraries - Initialize them if needed, or do it per-request
import openai
import anthropic
import google.generativeai as genai


app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration (could be moved to a config file or env vars)
DEBUG_MODE = os.environ.get('FLASK_DEBUG_MODE', 'True').lower() == 'true'
PORT = int(os.environ.get('FLASK_PORT', 8000))
# REVIT_LISTENER_URL = "http://localhost:8001" # Not currently used by chat_api but kept for context

@app.route('/', methods=['GET'])
def chat_ui():
    """Serves the main chat UI page."""
    return render_template('index.html')

@app.route('/chat_api', methods=['POST'])
def chat_api():
    """Handles messages from the chat UI and returns a model response."""
    data = request.json
    conversation_history = data.get('conversation') # Expecting a list of {'role': ..., 'content': ...}
    api_key = data.get('apiKey')
    selected_model = data.get('model')

    if not conversation_history or not isinstance(conversation_history, list) or not conversation_history[-1].get('content'):
        return jsonify({"error": "No message or invalid conversation history provided"}), 400
    if not selected_model:
        return jsonify({"error": "No model selected"}), 400
    
    user_message = conversation_history[-1]['content'] # The last message is the current user input

    # API key is required for all non-echo models
    if selected_model != 'echo_model' and not api_key:
        return jsonify({"error": "API key is required for this model"}), 400

    model_reply = ""
    error_message = None

    try:
        if selected_model == 'echo_model':
            model_reply = (
                f"Server echoes: '{user_message}'. "
                f"Model selected: '{selected_model}'. "
                f"API Key provided: '{bool(api_key)}'. "
                f"History items: {len(conversation_history)}."
            )
        
        # --- OpenAI Models --- 
        elif selected_model.startswith('gpt-') or selected_model.startswith('o1'):
            client = openai.OpenAI(api_key=api_key)
            # OpenAI expects messages in a specific format
            messages_for_openai = []
            for msg in conversation_history:
                role = msg.get('role')
                content = msg.get('content')
                if role == 'bot': # OpenAI uses 'assistant' for bot replies
                    role = 'assistant'
                if role and content:
                    messages_for_openai.append({"role": role, "content": content})
            
            if not messages_for_openai:
                 raise ValueError("Message list for OpenAI cannot be empty after filtering.")

            completion = client.chat.completions.create(
                model=selected_model,
                messages=messages_for_openai
            )
            model_reply = completion.choices[0].message.content

        # --- Anthropic Models --- 
        elif selected_model.startswith('claude-'):
            client = anthropic.Anthropic(api_key=api_key)
            # Anthropic expects messages, and optionally a system prompt
            # For simplicity, we'll treat all prior messages as the conversation history.
            # The user's current message is the last one in the history.
            
            messages_for_anthropic = []
            system_prompt = None # Optional: extract if you have a specific system message role
            
            # Anthropic format: user/assistant turns. User message must be first.
            # If history starts with bot, we might need to prepend a dummy user message or adjust.
            # For now, assume history is validly formatted by the client.
            for i, msg in enumerate(conversation_history):
                role = msg.get('role')
                content = msg.get('content')
                if role and content:
                    if role == 'bot': # Anthropic uses 'assistant' for bot replies
                        messages_for_anthropic.append({"role": "assistant", "content": content})
                    else: # user or system (system usually first)
                        messages_for_anthropic.append({"role": "user", "content": content})
            
            if not messages_for_anthropic or messages_for_anthropic[-1]["role"] != "user":
                raise ValueError("Anthropic requires the last message to be from the user, or message list is empty.")

            # The main message to send is the last user message, history provides context.
            # Anthropic Python SDK v0.3+ uses messages API where last message is user's.
            response = client.messages.create(
                model=selected_model,
                max_tokens=1024, # Adjust as needed
                messages=messages_for_anthropic
            )
            model_reply = response.content[0].text

        # --- Google Gemini Models --- (Updated for google-generativeai >= 0.4.0)
        elif selected_model.startswith('gemini-'):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(selected_model)

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
            error_message = f"Model '{selected_model}' is not recognized or supported."
            return jsonify({"error": error_message}), 501 # Not Implemented

    except openai.APIError as e:
        error_message = f"OpenAI API Error: {str(e)}"
    except anthropic.APIError as e:
        error_message = f"Anthropic API Error: {str(e)}"
    except Exception as e: # Catch-all for other errors, including Google specific ones for now
        if hasattr(e, 'message') and e.message: # General exception message
             error_message = f"Error with {selected_model}: {e.message}"
        elif hasattr(e, 'args') and e.args: # Some exceptions store messages in args
            error_message = f"Error with {selected_model}: {e.args[0] if e.args else str(e)}"
        else:
            error_message = f"An unexpected error occurred with {selected_model}: {str(e)}"
        print(f"Error details for {selected_model}: {type(e).__name__} - {str(e)}") # Log detailed error

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

    print("External Server: Received request from client: {}".format(client_request_data))
    print("External Server: Forwarding command '{}' to Revit Listener at {}".format(revit_command_payload.get('command'), REVIT_LISTENER_URL))

    try:
        response_from_revit = requests.post(
            REVIT_LISTENER_URL, 
            json=revit_command_payload, 
            headers={'Content-Type': 'application/json'}, 
            timeout=30
        )
        response_from_revit.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        revit_response_data = response_from_revit.json()
        print("External Server: Received response from Revit Listener: {}".format(revit_response_data))
        
        return jsonify(revit_response_data), response_from_revit.status_code

    except requests.exceptions.ConnectionError as e:
        error_msg = "External Server: Could not connect to Revit Listener at {}. Is it running? Error: {}".format(REVIT_LISTENER_URL, e)
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
    # Ensure templates and static folders are correctly referenced if script is run directly
    # This is usually handled by Flask when run with `flask run` but good for `python server.py`
    app.run(debug=DEBUG_MODE, port=PORT, host='0.0.0.0') 