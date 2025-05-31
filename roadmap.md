# RevitMCP Tools Roadmap

This document outlines the plan for developing tools (API endpoints) for the RevitMCP extension, enabling more advanced interaction with Revit models via an AI assistant.

## Goals

*   Allow users to query elements based on various criteria.
*   Retrieve element properties.
*   Select elements in the Revit UI.
*   Modify element parameters.

## Proposed Tools & Status

| Tool / API Endpoint                         | HTTP Method | Description                                                                     | Input Parameters/Body                                                                                                | Output                                                                                                   | Status      |
| :------------------------------------------ | :---------- | :------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------- | :---------- |
| **Project Information**                     |             |                                                                                 |                                                                                                                      |                                                                                                          |             |
| `/project_info`                             | GET         | Get basic project information.                                                  | None                                                                                                                 | JSON object with project details.                                                                        | Implemented |
| **Element Retrieval & Filtering**           |             |                                                                                 |                                                                                                                      |                                                                                                          |             |
| `/elements/by_category`                     | GET         | Get basic info (ID, Name) for all elements of a specified category.             | `category_name` (string, e.g., "OST_Doors")                                                                      | List of `{"id": ..., "name": ...}` objects.                                                            | To Do       |
| `/elements/filter`                          | POST        | Get elements based on category and other parameter filters (advanced).          | JSON: `{"category_name": ..., "level_name": ..., "parameters": [{"name": ..., "value": ..., "condition": ...}]}` | List of `{"id": ..., "name": ...}` objects.                                                            | To Do       |
| **Element Properties**                      |             |                                                                                 |                                                                                                                      |                                                                                                          |             |
| `/elements/get_properties`                  | POST        | Get detailed parameter values for a list of specified element IDs.              | JSON: `{"element_ids": [...], "parameter_names": [...]}`                                                        | List of `{"id": ..., "properties": {"param1": ..., "param2": ...}}` objects.                         | To Do       |
| **Element Interaction**                     |             |                                                                                 |                                                                                                                      |                                                                                                          |             |
| `/elements/select`                          | POST        | Select specified elements in the Revit UI.                                      | JSON: `{"element_ids": [...]}`                                                                                    | JSON: `{"status": ..., "message": ..., "selected_ids": [...], "not_found_ids": [...]}`                 | To Do       |
| `/elements/update_parameters`               | POST        | Update parameters for one or more elements.                                     | JSON: `[{"element_id": ..., "parameters": {"param1": ..., "param2": ...}}]`                                  | List of `{"element_id": ..., "status": ..., "updated_params": [...], "errors": {...}}` objects.         | To Do       |

## Development Workflow for Each Tool

1.  **Define in `startup.py`:** Add the route and handler function to `RevitMCP.extension/startup.py`.
2.  **Implement Revit API Logic:** Write the core logic using the Revit API within the handler function.
3.  **Test (Revit-Side):**
    *   Reload pyRevit / Restart Revit.
    *   Use `curl` or Postman to directly test the new pyRevit route (e.g., `http://localhost:48884/revit-mcp-v1/...`).
4.  **Update External Server (`server.py`):
    *   Add a new Python function in `server.py` that calls the new pyRevit route.
    *   Define a corresponding "tool specification" for the AI model (e.g., in `mcp_tools_specs`).
5.  **Test (Full Chain):** Test the entire workflow from the AI assistant (or a simulated call to the `server.py` tool function).
6.  **Update `roadmap.md`:** Mark the tool's status as "In Progress" or "Implemented".
7.  **Update `README.md`:** Add documentation for the new tool/endpoint.

## Notes on AI Interaction

The AI model will act as an orchestrator. For complex tasks (e.g., "Find all doors on Level 1 that are wider than 900mm, show me their fire rating, then select them"), the AI will make a sequence of calls to these tools:
1.  Call `/elements/filter` (or `/elements/by_category` then filter results if `/elements/filter` is not yet ready).
2.  Call `/elements/get_properties` with the IDs from step 1, asking for "Fire Rating".
3.  Display the fire ratings.
4.  Call `/elements/select` with the IDs from step 1. 