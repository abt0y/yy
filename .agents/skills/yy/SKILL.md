```markdown
# yy Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the `yy` Python repository. You'll learn how to structure files, write imports and exports, and follow the project's commit and testing styles. This guide also provides step-by-step instructions for common workflows and suggested commands to streamline your development process.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `my_module.py`, `data_processor.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import helper_function
    ```

### Export Style
- Use **named exports**; explicitly define what is exported from each module.
  - Example:
    ```python
    __all__ = ['MyClass', 'my_function']
    ```

### Commit Patterns
- Commit messages are freeform, with no enforced prefix.
- Average commit message length: ~29 characters.
  - Example:
    ```
    Fix bug in data parsing logic
    ```

## Workflows

### Creating a New Module
**Trigger:** When adding new functionality to the codebase  
**Command:** `/new-module`

1. Create a new Python file using snake_case naming (e.g., `feature_xyz.py`).
2. Implement your functions or classes.
3. Use relative imports to reference other modules.
4. Define `__all__` to specify exported symbols.
5. Write or update corresponding test files (`feature_xyz.test.py`).

### Running Tests
**Trigger:** When you need to verify code correctness  
**Command:** `/run-tests`

1. Identify test files matching the `*.test.*` pattern.
2. Run tests using your preferred Python test runner (e.g., `pytest`, `unittest`).
   - Example:
     ```bash
     pytest feature_xyz.test.py
     ```
3. Review and fix any failing tests.

### Writing Commits
**Trigger:** When saving changes to version control  
**Command:** `/commit`

1. Write a concise, descriptive commit message (~29 characters).
2. No need for specific prefixes.
   - Example:
     ```
     Update data processing logic
     ```

## Testing Patterns

- Test files follow the `*.test.*` naming pattern (e.g., `module.test.py`).
- The specific testing framework is not enforced or detected.
- Place test files alongside the modules they test or in a dedicated test directory.

**Example test file:**
```python
# my_module.test.py

from .my_module import my_function

def test_my_function():
    assert my_function(2, 3) == 5
```

## Commands
| Command       | Purpose                                      |
|---------------|----------------------------------------------|
| /new-module   | Scaffold a new module with conventions       |
| /run-tests    | Run all tests matching the test file pattern |
| /commit       | Make a commit following message guidelines   |
```
