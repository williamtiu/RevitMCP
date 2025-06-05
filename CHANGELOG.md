# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (conceptually, for now).

## [0.1.0] - 2024-07-30

This is the initial conceptual release incorporating a significant set of features for the RevitMCP External Server.

### Added

-   **Enhanced Ollama LLM Support:**
    -   Integration with local Ollama models via an OpenAI-compatible API endpoint (`/v1/chat/completions`).
    -   Full tool-calling capabilities extended to compatible Ollama models, allowing them to use all defined Revit tools.
    -   New UI configuration in settings modal for specifying Ollama Server URL, a custom Ollama Model Name, and an optional API Key/Bearer Token for proxy authentication.
    -   Main model selector updated to a single "Ollama (Configure in Settings)" option.
-   **New Revit Element Creation Tools:**
    -   `create_wall` tool: Allows LLMs to request the creation of walls with specified type, level, start/end points, and optional height/structural properties.
    -   `create_floor` tool: Allows LLMs to request the creation of floors based on type, level, a list of boundary points, and optional structural property.
    -   `create_duct` tool: Allows LLMs to request the creation of ducts, specifying system type, duct type, level, start/end points, and dimensions.
    -   These new tools are available to all supported LLM providers (OpenAI, Anthropic, Google, Ollama) and are integrated into the `plan_and_execute_workflow_tool`.
-   **Web UI Test Cases:**
    -   Added a "Test Cases" button and modal in the web UI, allowing users to execute predefined prompts for testing various functionalities, including the new creation tools.
-   **Comprehensive User Documentation (`README.md`):**
    -   Major overhaul of `README.md` to include detailed sections for:
        -   Project Description
        -   Installation Instructions
        -   Quick Start Guide (including detailed Ollama setup)
        -   Configuration Options (all UI settings detailed)
        -   Frequently Asked Questions (FAQ)
        -   Troubleshooting Guide
        -   Contact/Support Information
    -   Updated Development Status & Task List table in `README.md`.
-   **Developer Documentation (Initial Files):**
    -   `CONTRIBUTING.md`: Added contribution guidelines covering bug reports, feature suggestions, PR process, code style, commit conventions, and testing.

### Changed

-   Ollama integration in `server.py` refactored multiple times:
    -   Initial simple completion via `/api/chat`.
    -   Refined to use `/v1/completions` based on initial feedback.
    -   Finally, updated to target `/v1/chat/completions` for robust, OpenAI-compatible tool calling.
-   Internal handling of Ollama parameters in `/chat_api` in `server.py` to support custom model names and optional tokens.
-   JavaScript in `index.html` updated to manage new Ollama settings and correctly pass them to the backend.

### Fixed

-   (Conceptually) Addressed potential error handling and response parsing for various LLM interactions during refactoring.
-   (Conceptually) Improved clarity and robustness of LLM tool specifications.
