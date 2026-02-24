# Endpoint Testing Guide

This guide explains how to use the test utilities and fixtures for testing the 46 stub endpoints being implemented in task 012.

## Overview

The endpoint testing infrastructure provides:

1. **FastAPI TestClient fixtures** - For making HTTP requests to endpoints
2. **Mock file system utilities** - For testing file-based operations
3. **Mock CLI command utilities** - For testing glab, gh, git, and claude CLI integrations
4. **Mock AI service utilities** - For testing AI-powered endpoints
5. **Test data factories** - For creating request/response test data
6. **Assertion helpers** - For common endpoint test assertions

## Quick Start

### Basic Endpoint Test

```python
def test_my_endpoint(client, assert_endpoint):
    """Test a simple endpoint."""
    # Act
    response = client.post("/api/my-endpoint", json={"key": "value"})

    # Assert
    assert_endpoint.assert_success_response(response)
```

### File-Based Endpoint Test

```python
def test_update_config(client, mock_file_system, assert_endpoint):
    """Test endpoint that updates a JSON config file."""
    # Arrange
    mock_file_system.write_json("config.json", {"setting": "old_value"})

    # Act
    response = client.patch("/api/config", json={"setting": "new_value"})

    # Assert
    assert_endpoint.assert_success_response(response)
    assert_endpoint.assert_file_updated(
        mock_file_system,
        "config.json",
        expected_content={"setting": "new_value"}
    )
```

### CLI Integration Endpoint Test

```python
def test_gitlab_command(client, mock_glab_cli, assert_endpoint):
    """Test endpoint that uses glab CLI."""
    # Arrange
    mock_glab_cli.mock_mr_update(mr_id=123, success=True)

    # Act
    response = client.post("/api/gitlab/merge-requests/123/approve")

    # Assert
    assert_endpoint.assert_success_response(response)
```

### AI Service Endpoint Test

```python
@pytest.mark.asyncio
async def test_ai_endpoint(client, mock_ai_service, assert_endpoint):
    """Test endpoint that uses AI service."""
    # Arrange
    mock_ai_service.configure_response(
        prompt="analyze code",
        response={"findings": ["issue1", "issue2"]}
    )

    # Act
    response = client.post("/api/analyze", json={"code": "..."})

    # Assert
    assert_endpoint.assert_success_response(response)
```

## Available Fixtures

### Client Fixtures

#### `client`
Basic FastAPI TestClient for making HTTP requests.

```python
def test_endpoint(client):
    response = client.get("/api/endpoint")
    assert response.status_code == 200
```

#### `authenticated_client`
TestClient with authentication headers already set.

```python
def test_protected_endpoint(authenticated_client):
    response = authenticated_client.get("/api/protected")
    assert response.status_code == 200
```

### File System Fixtures

#### `mock_file_system`
Mock file system for testing file operations.

```python
def test_file_ops(mock_file_system):
    # Write JSON file
    mock_file_system.write_json("test.json", {"key": "value"})

    # Read JSON file
    data = mock_file_system.read_json("test.json")
    assert data["key"] == "value"

    # Check if file exists
    assert mock_file_system.exists("test.json")

    # List files
    files = mock_file_system.list_files()
    assert "test.json" in files
```

#### `mock_claude_profiles`
Pre-populated claude-profiles.json file.

```python
def test_profile_endpoint(client, mock_claude_profiles):
    file_system, profiles_data = mock_claude_profiles

    # profiles_data contains sample profile data
    assert len(profiles_data["profiles"]) == 2

    # File system has the file
    assert file_system.exists("claude-profiles.json")
```

#### `mock_api_profiles`
Pre-populated api-profiles.json file.

#### `mock_roadmap_json`
Pre-populated roadmap.json file.

#### `mock_ideation_json`
Pre-populated ideation.json file.

### CLI Mock Fixtures

#### `mock_subprocess`
Generic subprocess mock for any CLI commands.

```python
def test_custom_cli(mock_subprocess):
    mock_subprocess.configure({
        "custom-cli command": {
            "returncode": 0,
            "stdout": "success output"
        }
    })

    # Your code that calls subprocess.run(["custom-cli", "command"])
```

#### `mock_glab_cli`
GitLab CLI (glab) command mock.

```python
def test_gitlab(mock_glab_cli):
    # Mock MR view
    mock_glab_cli.mock_mr_view(123, {"title": "Test MR"})

    # Mock MR update
    mock_glab_cli.mock_mr_update(123, success=True)

    # Mock custom command
    mock_glab_cli.mock_command("issue list", output="...")
```

#### `mock_gh_cli`
GitHub CLI (gh) command mock.

```python
def test_github(mock_gh_cli):
    # Mock PR view
    mock_gh_cli.mock_pr_view(456, {"title": "Test PR"})

    # Mock issue view
    mock_gh_cli.mock_issue_view(789, {"title": "Test Issue"})
```

### AI/Background Service Fixtures

#### `mock_ai_service`
Mock AI service for testing AI-powered endpoints.

```python
def test_ai(mock_ai_service):
    mock_ai_service.configure_response(
        prompt="generate ideas",
        response={"ideas": ["idea1", "idea2"]}
    )

    result = await mock_ai_service.generate(prompt="generate ideas")
    assert len(result["ideas"]) == 2
```

#### `mock_background_task`
Mock background task service.

```python
def test_background(mock_background_task):
    # Start task
    task_id = mock_background_task.start("process_data", data="...")

    # Check status
    assert mock_background_task.get_status(task_id) == "running"

    # Complete task
    mock_background_task.complete(task_id, result={"processed": True})
    assert mock_background_task.get_status(task_id) == "completed"
```

### Test Data Factory

#### `test_data_factory`
Factory for creating standard request/response test data.

```python
def test_with_factory(client, test_data_factory):
    # Create API key request
    request = test_data_factory.settings_api_key_request(
        api_key="sk-ant-test"
    )

    # Create profile request
    request = test_data_factory.settings_profile_request(
        profile_id="profile-1"
    )

    # Create feature status request
    request = test_data_factory.roadmap_feature_status_request(
        feature_id="feature-1",
        status="completed"
    )

    # Create success response
    response = test_data_factory.success_response({"data": "value"})

    # Create error response
    response = test_data_factory.error_response(
        message="Error occurred",
        code="validation_error"
    )
```

### Assertion Helpers

#### `assert_endpoint`
Helper assertions for endpoint testing.

```python
def test_assertions(client, assert_endpoint):
    response = client.get("/api/test")

    # Assert success
    assert_endpoint.assert_success_response(response)

    # Assert success with expected data
    assert_endpoint.assert_success_response(
        response,
        expected_data={"key": "value"}
    )

    # Assert error
    assert_endpoint.assert_error_response(
        response,
        expected_status=400,
        expected_message="Invalid input"
    )

    # Assert file was updated
    assert_endpoint.assert_file_updated(
        mock_file_system,
        "config.json",
        expected_content={"updated": True}
    )

    # Assert CLI was called
    assert_endpoint.assert_cli_called(
        mock_subprocess,
        "git status"
    )
```

### Integration Test Helper

#### `endpoint_integration_helper`
Comprehensive helper combining all utilities.

```python
def test_integration(endpoint_integration_helper):
    helper = endpoint_integration_helper

    # Access all utilities through helper
    helper.client              # TestClient
    helper.file_system         # Mock file system
    helper.subprocess          # Mock subprocess
    helper.ai_service          # Mock AI service
    helper.data_factory        # Test data factory
    helper.assert_endpoint     # Assertion helpers

    # Example usage
    helper.file_system.write_json("test.json", {})
    response = helper.client.post("/api/test")
    helper.assert_endpoint.assert_success_response(response)
```

## Testing Patterns by Endpoint Type

### File-Based Operations (26 endpoints)

Test pattern for endpoints that read/modify JSON files:

```python
class TestFileBasedEndpoints:
    def test_update_json_file(self, client, mock_file_system, assert_endpoint):
        """Test endpoint that updates a JSON configuration file."""
        # Arrange - Create initial file state
        initial_data = {"setting": "value"}
        mock_file_system.write_json("config.json", initial_data)

        # Act - Call endpoint
        response = client.patch(
            "/api/config",
            json={"setting": "new_value"}
        )

        # Assert - Verify response and file update
        assert_endpoint.assert_success_response(response)

        updated_data = mock_file_system.read_json("config.json")
        assert updated_data["setting"] == "new_value"
```

### CLI Integration (11 endpoints)

Test pattern for endpoints that execute CLI commands:

```python
class TestCLIEndpoints:
    def test_cli_command(self, client, mock_glab_cli, assert_endpoint):
        """Test endpoint that executes glab CLI command."""
        # Arrange - Mock CLI response
        mock_glab_cli.mock_command(
            "mr approve 123",
            output="MR approved",
            returncode=0
        )

        # Act - Call endpoint
        response = client.post("/api/gitlab/merge-requests/123/approve")

        # Assert - Verify success
        assert_endpoint.assert_success_response(response)
```

### AI Services (9 endpoints)

Test pattern for AI-powered endpoints:

```python
class TestAIEndpoints:
    @pytest.mark.asyncio
    async def test_ai_endpoint(self, client, mock_ai_service, assert_endpoint):
        """Test endpoint that uses AI service."""
        # Arrange - Configure AI response
        mock_ai_service.configure_response(
            prompt="analyze",
            response={"analysis": "result"}
        )

        # Act - Call endpoint
        response = client.post(
            "/api/analyze",
            json={"content": "..."}
        )

        # Assert - Verify response
        assert_endpoint.assert_success_response(response)
        data = response.json()
        assert "analysis" in data or "task_id" in data
```

## Error Handling Tests

Always test error scenarios:

```python
class TestErrorHandling:
    def test_file_not_found(self, client, assert_endpoint):
        """Test handling when config file doesn't exist."""
        response = client.get("/api/config")
        assert_endpoint.assert_error_response(
            response,
            expected_status=404,
            expected_message="Config not found"
        )

    def test_cli_not_available(self, client, mock_subprocess, assert_endpoint):
        """Test handling when CLI tool is not installed."""
        mock_subprocess.configure({
            "glab --version": {
                "returncode": 127,
                "stderr": "command not found"
            }
        })

        response = client.post("/api/gitlab/test")
        assert_endpoint.assert_error_response(
            response,
            expected_status=500,
            expected_message="glab CLI not available"
        )

    def test_invalid_input(self, client, assert_endpoint):
        """Test validation of request data."""
        response = client.post(
            "/api/config",
            json={"invalid": "data"}
        )
        assert_endpoint.assert_error_response(
            response,
            expected_status=400
        )
```

## Integration Workflow Tests

Test complete workflows using multiple endpoints:

```python
class TestWorkflows:
    def test_complete_workflow(self, endpoint_integration_helper):
        """Test multi-step workflow across endpoints."""
        helper = endpoint_integration_helper

        # Step 1: Create resource
        response = helper.client.post("/api/resource", json={...})
        helper.assert_endpoint.assert_success_response(response)
        resource_id = response.json()["id"]

        # Step 2: Update resource
        response = helper.client.patch(
            f"/api/resource/{resource_id}",
            json={...}
        )
        helper.assert_endpoint.assert_success_response(response)

        # Step 3: Verify final state
        response = helper.client.get(f"/api/resource/{resource_id}")
        data = response.json()
        assert data["status"] == "expected_status"
```

## Best Practices

1. **Arrange-Act-Assert Pattern**: Structure tests clearly with setup, execution, and verification phases

2. **Use Descriptive Test Names**: Test function names should describe what is being tested

3. **Test Both Success and Error Cases**: Always include negative tests

4. **Mock External Dependencies**: Use provided fixtures to mock file systems, CLI commands, and AI services

5. **Test One Thing**: Each test should verify a single behavior

6. **Clean Test Data**: Use fixtures to ensure clean state for each test

7. **Document Complex Tests**: Add docstrings explaining what the test validates

## Running Tests

```bash
# Run all endpoint tests
pytest tests/test_endpoints_*.py

# Run specific test file
pytest tests/test_endpoints_settings.py

# Run specific test
pytest tests/test_endpoints_settings.py::test_update_api_key

# Run with coverage
pytest --cov=apps.web-server.server.routes tests/

# Run in verbose mode
pytest -v tests/
```

## Example: Complete Test File

See `tests/test_endpoints_sample.py` for a complete example demonstrating all testing patterns.

## Troubleshooting

### Import Errors

If you get import errors, ensure pytest is discovering the modules correctly:

```bash
# Add apps/web-server/server to Python path
export PYTHONPATH="${PYTHONPATH}:apps/web-server/server"
pytest tests/
```

### Fixture Not Found

Ensure fixtures are imported in `conftest.py`:

```python
from tests.endpoint_test_utils import (
    client,
    mock_file_system,
    # ... other fixtures
)
```

### Mock Not Working

Verify the mock is configured before the code under test runs:

```python
# Correct
mock_subprocess.configure({...})  # Configure first
response = client.post("/api/test")  # Then call endpoint

# Incorrect
response = client.post("/api/test")  # Endpoint runs before mock configured
mock_subprocess.configure({...})
```

## Contributing

When adding new test utilities:

1. Add the utility to `tests/endpoint_test_utils.py`
2. Export it in `conftest.py` if it should be globally available
3. Document usage in this README
4. Add example tests to `test_endpoints_sample.py`
