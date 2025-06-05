# RevitMCP: Revit Model Content Protocol Extension

## Introduction

RevitMCP (Revit Model Content Protocol) is a pyRevit extension that allows external applications, such as AI assistants or other services, to interact with a running instance of Autodesk Revit. It achieves this by exposing an HTTP API from within Revit using pyRevit's "Routes" functionality. An external server component (typically `server.py` in this project) acts as an intermediary, which the external application communicates with. This intermediary server then makes calls to the API hosted by pyRevit within Revit.

This README provides instructions on how to set up and use the `RevitMCP.extension`.

## Prerequisites

1.  **Autodesk Revit:** A compatible version of Autodesk Revit must be installed.
2.  **pyRevit:** pyRevit must be installed for your Revit version. If you don't have it, download and install it from [pyrevitlabs.io](https://pyrevitlabs.io/).

## Installation

1.  **Install pyRevit:**
    *   Follow the official installation guide on the [pyRevit website](https://pyrevitlabs.io/docs/pyrevit/installer).

2.  **Install the `RevitMCP.extension`:**
    *   Locate your pyRevit extensions folder. You can typically find this by:
        *   Opening pyRevit Settings in Revit (pyRevit Tab -> Settings).
        *   Going to the "Extensions" section. It might show registered extension paths.
        *   Common default locations include:
            *   `%APPDATA%/pyRevit/Extensions`
            *   `%PROGRAMDATA%/pyRevit/Extensions`
    *   Copy the entire `RevitMCP.extension` folder (which contains `startup.py`, `lib/`, etc.) into one of your pyRevit extensions directories.

3.  **Reload pyRevit / Restart Revit:**
    *   After copying the extension, either "Reload" pyRevit (from the pyRevit tab in Revit) or restart Revit to ensure the extension is recognized and its `startup.py` script is executed.

## Configuration

1.  **Enable pyRevit Routes Server:**
    *   Open Revit.
    *   Go to the **pyRevit Tab -> Settings**.
    *   Find the section related to **"Routes"** or **"Web Server"** or **"API"**.
    *   **Enable the Routes server.**
    *   Note the **default port number**, which is typically `48884` for the first Revit instance. Subsequent Revit instances will use incrementing port numbers (e.g., `48885`, `48886`). Your external server (`server.py`) must be configured to point to the correct port.
    *   **Restart Revit** after enabling the Routes server if prompted or to ensure the settings take effect. The `startup.py` script in `RevitMCP.extension` defines the API endpoints when pyRevit loads.

2.  **Firewall/Network Access:**
    *   When the pyRevit Routes server starts for the first time, your operating system's firewall might ask for permission to allow Revit (or the Python process within Revit) to open a network port and listen for incoming connections. You must **allow this access** for the system to work.
    *   Ensure that no other firewall or security software is blocking connections to the port used by the pyRevit Routes server (e.g., `48884`).

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

## Troubleshooting

*   **Route Not Found Errors (`RouteHandlerNotDefinedException`):**
    *   Ensure `RevitMCP.extension/startup.py` exists and contains the route definitions.
    *   Reload pyRevit or Restart Revit after any changes to `startup.py`.
    *   Check pyRevit logs for messages from `startup.py` indicating it ran and defined the routes.
    *   Ensure the pyRevit Routes server is enabled in pyRevit Settings and Revit was restarted.
    *   Use the diagnostic script (provided during development) in a pyRevit-aware Python console within Revit to check `routes.get_routes("revit-mcp-v1")` and `routes.get_active_server()`.

*   **Connection Refused / Cannot Connect to pyRevit Routes API:**
    *   Verify the pyRevit Routes server is enabled in pyRevit Settings.
    *   Confirm the port number used by the external server to call the pyRevit API matches the port the pyRevit Routes server is actually listening on (default `48884`).
    *   Check firewall settings.

*   **Check Logs:**
    *   **pyRevit Logs:** (pyRevit Tab -> Settings -> Logging) for errors related to `RevitMCP.extension` loading, `startup.py` execution, or the Routes server.
    *   **External Server (`server.py`) Logs:** Check the console output of your `server.py` for errors when it tries to communicate with the pyRevit Routes API or when it's handling requests from the client application.

---
This README should help users set up and understand the RevitMCP system. 