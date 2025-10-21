from cover_agent.lsp_logic.utils.utils_adapt_command import adapt_test_command

# og = "coverage run -m pytest --cov=. -- --verbose"
# og = "mvn test -Dtest.parallel=true -DforkCount=4"
# og = "gradle test --parallel --max-workers=4 --continue"
# og = "pytest --maxfail=1 --disable-warnings -q"
# og = "mvn test -DskipIntegrationTests=true"
# og = "jest --runInBand --detectOpenHandles"
# og = "npm test -- --watchAll=false"
# print(og)
# print(adapt_test_command(og, "./lol"))
# test_cases = [
#     ("pytest --cov=src --verbose tests/", "tests/unit/test_auth.py"),
#     ("jest --coverage --watch", "src/components/Button.test.js"),
#     ("go test ./... -v -race", "internal/auth/auth_test.go"),
#     ("mvn test -Dtest=OldTest", "src/test/java/NewTest.java"),
#     ("rspec --format documentation", "spec/models/user_spec.rb"),
# ]
#
# for command, file_path in test_cases:
#     result = adapt_test_command(command, file_path)
#     print(f"Original: {command}")
#     print(f"Adapted:  {result}")
import pytest
from typing import Optional

# Function signature we're testing:
# def adapt_test_command_for_single_file(test_command: str, test_file_path: str) -> str

class TestAdaptTestCommandForSingleFile:
    """Test suite for rule-based test command adaptation function."""

    # Python/pytest test cases
    def test_pytest_basic(self):
        """Test basic pytest command."""
        result = adapt_test_command("pytest", "tests/test_utils.py")
        assert result == "pytest tests/test_utils.py"

    def test_pytest_with_flags(self):
        """Test pytest with various flags."""
        result = adapt_test_command(
            "pytest -v --tb=short", 
            "tests/test_api.py"
        )
        assert result == "pytest -v --tb=short tests/test_api.py"

    def test_pytest_with_coverage(self):
        """Test pytest with coverage options."""
        result = adapt_test_command(
            "pytest --cov=src --cov-report=html --cov-report=term-missing",
            "tests/integration/test_database.py"
        )
        assert result == "pytest --cov=src --cov-report=html --cov-report=term-missing tests/integration/test_database.py"

    def test_pytest_with_existing_file_arg(self):
        """Test pytest that already has a file argument - should replace it."""
        result = adapt_test_command(
            "pytest tests/", 
            "tests/test_specific.py"
        )
        assert result == "pytest tests/test_specific.py"

    def test_pytest_with_multiple_paths(self):
        """Test pytest with multiple existing paths - should replace them."""
        result = adapt_test_command(
            "pytest tests/ src/", 
            "tests/test_one.py"
        )
        assert result == "pytest tests/test_one.py"

    def test_python_m_pytest(self):
        """Test python -m pytest format."""
        result = adapt_test_command(
            "python -m pytest -v", 
            "tests/test_module.py"
        )
        assert result == "python -m pytest -v tests/test_module.py"

    # Node.js/Jest test cases
    def test_npm_test_basic(self):
        """Test basic npm test command."""
        result = adapt_test_command(
            "npm test", 
            "src/components/__tests__/Button.test.js"
        )
        assert result == "npm test -- src/components/__tests__/Button.test.js"

    def test_npm_run_test(self):
        """Test npm run test command."""
        result = adapt_test_command(
            "npm run test", 
            "tests/utils.test.js"
        )
        assert result == "npm run test -- tests/utils.test.js"

    def test_yarn_test(self):
        """Test yarn test command."""
        result = adapt_test_command(
            "yarn test", 
            "src/__tests__/App.test.tsx"
        )
        assert result == "yarn test -- src/__tests__/App.test.tsx"

    def test_jest_direct(self):
        """Test direct Jest command."""
        result = adapt_test_command(
            "jest --coverage", 
            "tests/api.test.js"
        )
        assert result == "jest --coverage tests/api.test.js"

    def test_npx_jest(self):
        """Test npx jest command."""
        result = adapt_test_command(
            "npx jest --watchAll=false", 
            "src/utils.test.ts"
        )
        assert result == "npx jest --watchAll=false src/utils.test.ts"

    # Java/Maven test cases
    def test_mvn_test_basic(self):
        """Test basic Maven test command."""
        result = adapt_test_command(
            "mvn test", 
            "src/test/java/com/example/UserServiceTest.java"
        )
        assert result == "mvn test -Dtest=UserServiceTest"

    def test_mvn_test_with_profile(self):
        """Test Maven test with profile."""
        result = adapt_test_command(
            "mvn test -Pintegration", 
            "src/test/java/com/example/integration/DatabaseTest.java"
        )
        assert result == "mvn test -Pintegration -Dtest=DatabaseTest"

    def test_mvn_test_nested_class(self):
        """Test Maven test with nested test class path."""
        result = adapt_test_command(
            "mvn test", 
            "src/test/java/com/company/module/service/UserServiceTest.java"
        )
        assert result == "mvn test -Dtest=UserServiceTest"

    # Java/Gradle test cases
    def test_gradle_test_basic(self):
        """Test basic Gradle test command."""
        result = adapt_test_command(
            "./gradlew test", 
            "src/test/java/com/example/CalculatorTest.java"
        )
        assert result == './gradlew test --tests "CalculatorTest"'

    def test_gradle_test_with_flags(self):
        """Test Gradle test with additional flags."""
        result = adapt_test_command(
            "./gradlew test --info", 
            "src/test/kotlin/com/example/ServiceTest.kt"
        )
        assert result == './gradlew test --info --tests "ServiceTest"'

    # Go test cases
    def test_go_test_all(self):
        """Test go test ./... command."""
        result = adapt_test_command(
            "go test ./...", 
            "internal/handlers/user_test.go"
        )
        assert result == "go test ./internal/handlers"

    def test_go_test_with_verbose(self):
        """Test go test with verbose flag."""
        result = adapt_test_command(
            "go test -v ./...", 
            "pkg/utils/math_test.go"
        )
        assert result == "go test -v ./pkg/utils"

    def test_go_test_with_coverage(self):
        """Test go test with coverage."""
        result = adapt_test_command(
            "go test -cover -race ./...", 
            "cmd/server/main_test.go"
        )
        assert result == "go test -cover -race ./cmd/server"

    def test_go_test_single_package(self):
        """Test go test on single package."""
        result = adapt_test_command(
            "go test ./internal/...", 
            "internal/auth/token_test.go"
        )
        assert result == "go test ./internal/auth"

    # Ruby/RSpec test cases
    def test_rspec_basic(self):
        """Test basic RSpec command."""
        result = adapt_test_command(
            "rspec", 
            "spec/models/user_spec.rb"
        )
        assert result == "rspec spec/models/user_spec.rb"

    def test_bundle_exec_rspec(self):
        """Test bundle exec rspec command."""
        result = adapt_test_command(
            "bundle exec rspec", 
            "spec/controllers/users_controller_spec.rb"
        )
        assert result == "bundle exec rspec spec/controllers/users_controller_spec.rb"

    def test_rspec_with_format(self):
        """Test RSpec with format options."""
        result = adapt_test_command(
            "rspec --format documentation", 
            "spec/services/auth_service_spec.rb"
        )
        assert result == "rspec --format documentation spec/services/auth_service_spec.rb"

    # C#/.NET test cases
    def test_dotnet_test_basic(self):
        """Test basic dotnet test command."""
        result = adapt_test_command(
            "dotnet test", 
            "tests/UserServiceTests.cs"
        )
        assert result == "dotnet test --filter FullyQualifiedName~UserServiceTests"

    def test_dotnet_test_with_project(self):
        """Test dotnet test with specific project."""
        result = adapt_test_command(
            "dotnet test MyProject.Tests.csproj", 
            "tests/Integration/DatabaseTests.cs"
        )
        assert result == "dotnet test MyProject.Tests.csproj --filter FullyQualifiedName~DatabaseTests"

    # Edge cases and complex scenarios
    def test_command_with_environment_variables(self):
        """Test command with environment variables."""
        result = adapt_test_command(
            "ENV=test pytest --tb=short", 
            "tests/test_env.py"
        )
        assert result == "ENV=test pytest --tb=short tests/test_env.py"

    def test_deeply_nested_test_file(self):
        """Test with deeply nested test file path."""
        result = adapt_test_command(
            "pytest", 
            "tests/unit/services/auth/providers/oauth/test_google.py"
        )
        assert result == "pytest tests/unit/services/auth/providers/oauth/test_google.py"

    def test_windows_path_separators(self):
        """Test with Windows-style path separators."""
        result = adapt_test_command(
            "pytest", 
            "tests\\unit\\test_utils.py"
        )
        # Should normalize to forward slashes or handle appropriately
        assert "test_utils.py" in result

    def test_test_file_without_extension(self):
        """Test with test file path without extension (edge case)."""
        result = adapt_test_command(
            "go test ./...", 
            "internal/handlers/user_test"
        )
        # Should still work for Go tests
        assert result == "go test ./internal/handlers"

    def test_relative_vs_absolute_paths(self):
        """Test handling of relative vs absolute paths."""
        result = adapt_test_command(
            "pytest", 
            "./tests/test_relative.py"
        )
        assert result == "pytest ./tests/test_relative.py"

    def test_command_already_targeting_specific_file(self):
        """Test command that already targets the same specific file."""
        result = adapt_test_command(
            "pytest tests/test_specific.py", 
            "tests/test_specific.py"
        )
        # Should return the same command since it's already correct
        assert result == "pytest tests/test_specific.py"

    def test_command_with_test_name_pattern(self):
        """Test command with existing test name patterns."""
        result = adapt_test_command(
            "pytest -k test_login", 
            "tests/test_auth.py"
        )
        # Should preserve the pattern but target the specific file
        assert result == "pytest -k test_login tests/test_auth.py"

    # Performance and boundary tests
    def test_very_long_command(self):
        """Test with very long command line."""
        long_flags = " ".join([f"--flag{i}=value{i}" for i in range(50)])
        command = f"pytest {long_flags}"
        result = adapt_test_command(command, "tests/test_long.py")
        assert result.endswith("tests/test_long.py")
        assert len(result) > len(command)

    def test_very_long_file_path(self):
        """Test with very long file path."""
        long_path = "/".join([f"level{i}" for i in range(20)]) + "/test_deep.py"
        result = adapt_test_command("pytest", long_path)
        assert result == f"pytest {long_path}"
