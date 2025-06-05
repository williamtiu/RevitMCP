# RevitMCP: Revit Model Content Protocol External Server

## Introduction

This document describes the **RevitMCP External Server**, a Python-based Flask application that acts as an intermediary between a Large Language Model (LLM) and a running instance of Autodesk Revit. The broader RevitMCP system leverages pyRevit to expose a Revit API, and this external server provides a user interface (chat) and handles communication with various LLM providers (OpenAI, Anthropic, Google Gemini, Ollama) to translate natural language commands into Revit actions.

The primary goal is to enable users to interact with and modify their Revit models using conversational AI, with the LLM planning and executing Revit operations via a suite of defined tools.

## Installation

1.  **Prerequisites:**
    *   Python 3.7+
    *   Access to a Revit installation (for the Revit-side listener, which is part of the broader RevitMCP extension).
    *   An Ollama server instance if you intend to use local LLMs via Ollama.
2.  **Setup:**
    *   Clone this repository (or ensure the `RevitMCP.extension/lib/RevitMCP_ExternalServer/` directory is available).
    *   Navigate to the `RevitMCP.extension/lib/RevitMCP_ExternalServer/` directory.
    *   Install required Python packages:
        ```bash
        pip install -r requirements.txt
        ```
3.  **Revit-Side Setup:**
    *   This external server is designed to work in conjunction with the main `RevitMCP.extension` for pyRevit. Ensure the accompanying RevitMCP extension (which includes the Revit listener component `startup.py`) is correctly installed and enabled in your pyRevit setup. Please refer to the documentation for the `RevitMCP.extension` for details on installing pyRevit extensions. The pyRevit listener must be active for this external server to communicate with Revit.

## Quick Start

1.  **Run the External Server:**
    Navigate to the `RevitMCP.extension/lib/RevitMCP_ExternalServer/` directory and run:
    ```bash
    python server.py
    ```
    By default, the server starts on `http://localhost:8000`. You can check the console output for the exact URL.
2.  **Open the Chat UI:**
    Open your web browser and go to `http://localhost:8000` (or the port shown in the server console).
3.  **Configure LLM Providers:**
    *   Click the settings icon (⋮) in the chat UI's sidebar.
    *   Enter your API keys for OpenAI, Anthropic, or Google Gemini as needed.
    *   **For Ollama:**
        *   Select "Ollama (Configure in Settings)" from the model dropdown in the main UI first (this makes it your "Preferred Model" if you save settings, or just the active one for the session).
        *   In Settings:
            *   Enter your Ollama server URL (e.g., `http://localhost:11434`).
            *   Enter the specific Ollama model name you wish to use (e.g., `llama3:instruct`, `mistral`).
            *   Optionally, provide an API key if your Ollama instance is behind a proxy requiring one (this is sent as a Bearer token).
    *   Save settings.
4.  **Select Model & Chat:**
    *   Choose your desired LLM provider and model from the dropdown in the main chat interface. If you configured Ollama, ensure "Ollama (Configure in Settings)" is selected.
    *   Start interacting with Revit by typing commands!

**Example Prompts:**
*   "What is the name of the current project?"
*   "List all walls in the model and store them."
*   "Select the walls you just listed."
*   (Using a configured Ollama model) "Create a 'Generic - 200mm' wall on 'Level 1' from x=0,y=0,z=0 to x=5000,y=0,z=0."
*   "Create a floor of type 'Generic - 150mm' on 'Level 1' with boundary points at (0,0,0), (10000,0,0), (10000,5000,0), and (0,5000,0)."
*   "Use the planner to: first, find all doors on Level 1; second, get their 'Width' property; third, select them."

## Configuration Options

All configurations are managed via the Settings modal (⋮ icon in the sidebar) in the web UI. These settings are stored in your browser's `localStorage`.

*   **OpenAI API Key:** Your secret API key for OpenAI services.
*   **Anthropic API Key:** Your secret API key for Anthropic services.
*   **Google API Key:** Your secret API key for Google Gemini services.
*   **Ollama Server URL:** The full URL of your running Ollama server (e.g., `http://localhost:11434`). This is required if using the "Ollama (Configure in Settings)" model.
*   **Ollama Model Name:** The specific model identifier for your Ollama server (e.g., `llama3:instruct`, `mistral`, `codellama:latest`). This name is passed directly to your Ollama server. Required for Ollama.
*   **Ollama API Key (Optional Token):** An optional Bearer token if your Ollama server is accessed through a proxy that requires authentication.
*   **Preferred Model:** Select your default model to be active when the UI loads. This applies to all providers, including the "Ollama (Configure in Settings)" option.

## Ollama Support

RevitMCP now supports integration with local LLMs through Ollama.

### Configuration

1.  Ensure your Ollama server is running.
2.  In the RevitMCP chat interface, click the settings icon (⚙️ or ⋮).
3.  Enter your Ollama server URL in the "Ollama Server URL" field (default is `http://localhost:11434`).
4.  Save the settings.
5.  Select an Ollama model from the "Ollama" group in the model selector (e.g., "Ollama - Mistral"). The name after "ollama-" (e.g., "mistral") will be used as the model name when communicating with your Ollama server. You can use "ollama-custom" and ensure the model name you want to use is available on your Ollama server (the server will use the part after "ollama-" if you selected "ollama-custom", so if you want to use a model named "my-special-model", you should ensure your Ollama server has "my-special-model" available and select "ollama-my-special-model" in the UI, or select "ollama-custom" and ensure your server has a model named "custom").

## Test Case UI

A "Test Cases" button (🧪) is available in the sidebar of the chat UI. Clicking this button opens a modal window with a list of predefined test prompts.
This allows for quick testing of various RevitMCP functionalities and LLM responses. Simply click on a test case button to send the predefined prompt to the selected LLM.

## Running the System

The system consists of two main parts that need to be running:

1.  **The Revit-Side API (Managed by `RevitMCP.extension` and pyRevit):**
    *   When Revit starts and pyRevit loads the `RevitMCP.extension`, the `startup.py` script within the extension automatically runs.
    *   This script defines the necessary API endpoints (e.g., `/revit-mcp-v1/project_info`) and registers them with the pyRevit Routes server running inside Revit.
    *   You can verify this by checking pyRevit logs for messages from `startup.py` (see Troubleshooting below).

2.  **The External Intermediary Server (e.g., `server.py`):**
    *   This is a separate Python application (likely a Flask or FastAPI server) that the end-user application (e.g., AI Assistant) communicates with.
    *   This server is responsible for:
        *   Receiving requests from the end-user application.
        *   Making HTTP calls to the pyRevit Routes API running inside Revit (e.g., to `http://localhost:48884/revit-mcp-v1/...`).
        *   Processing the response from Revit and sending it back to the end-user application.
    *   **Launching this server:** The `RevitMCP.extension` includes a UI panel in Revit (e.g., "Server.panel") with a button like "Launch RevitMCP". This button is typically configured to start this external `server.py` script.
        *   Click this button in the Revit UI to start the intermediary server.
        *   Check the console output of this server to ensure it starts correctly and is listening on its configured port (e.g., your logs showed it running on port `8000`).

    **User Interface for the External Server:**
    *   Once the external server (`server.py`) is running, you typically interact with it through a web-based chat interface (often served at `http://localhost:PORT` where `PORT` is the one for `server.py`, e.g., `8000`).
    *   This interface usually provides:
        *   A **dropdown menu** to select the desired AI model (e.g., Anthropic, OpenAI, Google Generative AI).
        *   A **settings area or popup** where you can input your API keys for the selected AI model provider. These keys are necessary for the server to make requests to the AI services.

**Workflow Summary:**
   `AI Assistant/Client App`  ->  `External Server (server.py on e.g., port 8000)`  ->  `pyRevit Routes API (in Revit on e.g., port 48884)`

## Development Status & Task List

| Task                                      | Version & Last Update              | Status      | Notes/Links                                                         |
|-------------------------------------------|------------------------------------|-------------|---------------------------------------------------------------------|
| Add Ollama support                        | 1.0.0_002_20240729                 | ✅ Done     | Implemented in `server.py`; refined with `/v1/completions` endpoint. |
| Add UI for Ollama URL and port input      | 1.0.0_001_20240729                 | ✅ Done     | Added to `index.html` settings modal                                |
| Add test cases in the web UI              | 1.0.0_001_20240729                 | ✅ Done     | Added modal and JS logic in `index.html`                            |
| Update documentation                      | 1.0.0_001_20240729                 | ✅ Done     | Updated README.md with new features & task table |
| Full Code Review for consistency          | 1.0.0_001_20240729                 | ✅ Done     | Conceptual review completed.                     |
| Comprehensive Task Tracking               | 1.0.0_001_20240729                 | ✅ Done     | This table is up-to-date.                        |
| Functionality Verification                |                                    | ⬜ Todo     | Requires live testing of all LLM integrations & features |
| Synchronized Documentation (README, comments) | 1.0.0_001_20240729                 | ✅ Done     | README updated; code comments reviewed.          |
| Final Step-by-Step Review                 | 1.0.0_001_20240729                 | ✅ Done     | This review.                                     |
| Create Wall and Floor Tools               | 1.0.0_003_20240729                 | ✅ Done     | Implemented in `server.py` & added to LLM specs.                  |
| Comprehensive README Update               | 1.0.0_003_20240729                 | ✅ Done     | This update.                                                        |

## FAQ

*   **Q: What are the `*.mcp_tool` functions in `server.py`?**
    A: These are Python functions registered with the `FastMCP` server instance using the `@mcp_server.tool()` decorator. This registration makes them available as "tools" that the configured LLMs can request to call as part of their response, enabling them to interact with Revit or perform other server-side actions. The server then dispatches these requests to the actual Python functions, which typically interact with Revit via the `call_revit_listener` function.

*   **Q: How does Ollama tool calling work?**
    A: The server uses Ollama's OpenAI-compatible `/v1/chat/completions` endpoint. Tool specifications are provided to the Ollama model in a format similar to OpenAI's function calling. The success of tool calling (i.e., the LLM correctly identifying when to use a tool and providing the right arguments) heavily depends on the specific Ollama model's capabilities to understand and respond to these function-calling prompts.

*   **Q: What units should I use when specifying coordinates or dimensions for creation tools?**
    A: For tools like `create_wall`, `create_floor`, etc., provide numerical values in Revit's internal units. Typically, this is decimal feet for length measurements if your Revit project template is imperial, or millimeters if your Revit project is metric. The LLM should be prompted accordingly if specific units are desired by the user (e.g., "create a wall 10 feet long"). For best results, prompt with numerical values assuming the Revit project's internal units, or explicitly state the units in the prompt and expect the LLM to handle any necessary conversion if it's capable.

*   **Q: Where can I find the list of available Revit categories or type names (e.g., for walls, floors)?**
    A: You can ask the assistant "What Revit categories are commonly available?" or "List available wall types in the project." These types of queries may rely on the LLM's general knowledge or specific tools designed to list types from the current project (if such tools are implemented). For precise names available in your specific Revit project, you might need to refer to your Revit project environment directly or use tools that can list these types (e.g., `get_elements_by_category` can show instance names, which might inform type usage).

## Troubleshooting

*   **Cannot connect to Revit Listener / Revit API:**
    *   Ensure the main `RevitMCP.extension` (including `startup.py`) is correctly installed and loaded in pyRevit within your Revit application.
    *   The external server (`server.py`) attempts to auto-detect the Revit listener port (common ports are 48884, 48885, 48886). Check the `server.py` console output for messages about which port it's trying to use or if detection failed (it defaults to 48884 if not detected).
    *   Verify that no firewall is blocking communication between the Python server (`server.py`) and Revit, especially if they are on the same machine (localhost).
    *   Check pyRevit logs within Revit for any errors related to the `RevitMCP.extension` or its routes.

*   **Ollama requests fail:**
    *   Ensure your Ollama server is running and accessible at the URL specified in the RevitMCP chat UI settings.
    *   Verify the model name specified in the settings (e.g., `llama3:instruct`) is available on your Ollama server. You can check this by running `ollama list` in your terminal where Ollama server is running.
    *   If using a proxy for Ollama, ensure the optional API key/Bearer token is correctly entered if required by your proxy.
    *   Check the `RevitMCP.extension/lib/RevitMCP_ExternalServer/server_logs/server_app.log` file for detailed error messages from the external server.

*   **LLM Tool calls don't work as expected:**
    *   Some LLMs (especially smaller local models or those not specifically fine-tuned for function calling) may struggle with complex tool use or generating correctly formatted JSON arguments. Try simpler prompts or be more explicit in your instructions to the LLM.
    *   Check the `server_app.log` for details on what arguments the LLM attempted to pass to the tool and any errors that occurred during tool execution.

*   **Element creation tools (`create_wall`, `create_floor`) fail:**
    *   Ensure the type names (e.g., "Generic - 200mm" for walls, "Generic - 150mm" for floors) exactly match type names available in your current Revit project. Case sensitivity might matter.
    *   Check that coordinates and geometric inputs are valid for Revit (e.g., floor boundaries must form closed, non-self-intersecting loops).
    *   Review the `server_app.log` and potentially the Revit journal files for more detailed error messages passed back from the Revit listener.

*   **General Issues:**
    *   Always check the `server_app.log` file located in `RevitMCP.extension/lib/RevitMCP_ExternalServer/server_logs/` for detailed error tracebacks.
    *   Ensure your `requirements.txt` are installed for the Python environment running `server.py`.

## Contact / Support

For issues, questions, or contributions, please open an issue on the GitHub repository for this project. (Please replace this with the actual link to your project's repository when available.)

---
This README should help users set up and understand the RevitMCP External Server system.