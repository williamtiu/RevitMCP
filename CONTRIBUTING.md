# Contributing to RevitMCP External Server

First off, thank you for considering contributing! Your help is essential for making this project better.

## How to Contribute

We welcome contributions in various forms, including feature enhancements, bug fixes, documentation improvements, and more.

### Reporting Bugs

-   Ensure the bug was not already reported by searching on GitHub under Issues.
-   If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample or an executable test case** demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements

-   Open a new issue with a clear title and description of the proposed enhancement.
-   Explain why this enhancement would be useful and provide as much detail as possible, including potential implementation ideas if you have them.

### Pull Request Process

1.  **Fork the Repository:** Start by forking the main repository to your own GitHub account.
2.  **Create a Feature Branch:** For any new feature or bug fix, create a new branch from the `main` (or `develop` if it exists) branch.
    ```bash
    git checkout -b feat/your-feature-name
    # or
    git checkout -b fix/your-bug-fix
    ```
3.  **Make Changes:** Implement your feature or bug fix.
    *   Ensure your code adheres to the style guidelines (see below).
    *   Write clear and concise commit messages (see below).
    *   Add or update tests for your changes.
4.  **Run Tests:** Ensure all tests pass.
    ```bash
    pytest
    ```
    *(Assuming pytest is the testing framework)*
5.  **Lint Your Code:** Ensure your code is formatted correctly.
    ```bash
    black .
    # Add other linters if applicable (e.g., flake8, prettier for JS)
    ```
6.  **Commit Your Changes:** Use Conventional Commits format for your commit messages (e.g., `feat: Add advanced Ollama configuration options`, `fix: Correct error handling for Revit listener timeout`).
7.  **Push to Your Fork:** Push your feature branch to your forked repository.
    ```bash
    git push origin feat/your-feature-name
    ```
8.  **Submit a Pull Request (PR):**
    *   Open a pull request from your feature branch to the main project's `main` (or `develop`) branch.
    *   Provide a clear description of the changes in your PR. Link to any relevant issues.
    *   Ensure your PR passes all CI checks.

## Code Style Guidelines

-   **Python:**
    *   Follow PEP 8.
    *   Use Black for automated code formatting.
    *   Include type hints for all function signatures.
    *   Write clear docstrings for all public modules, classes, and functions.
-   **JavaScript (for UI in `index.html`):**
    *   Use Prettier for code formatting (or a similar standard).
    *   Follow common best practices for clarity and maintainability.
-   **General:**
    *   Use meaningful names for variables, functions, and classes.
    *   Write self-documenting code where possible, supplemented by comments for complex logic.

## Commit Message Conventions

Please follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. This helps in automating changelog generation and makes the commit history more readable.

Common types include:
-   `feat:` (new feature)
-   `fix:` (bug fix)
-   `docs:` (documentation changes)
-   `style:` (formatting, missing semi colons, etc.; no code change)
-   `refactor:` (refactoring production code)
-   `test:` (adding missing tests, refactoring tests; no production code change)
-   `chore:` (updating grunt tasks etc; no production code change)

## Testing

-   All new features should include appropriate tests.
-   All bug fixes should include a regression test.
-   Ensure `pytest` (or the project's designated test runner) passes before submitting a PR.

Thank you for your contribution!
