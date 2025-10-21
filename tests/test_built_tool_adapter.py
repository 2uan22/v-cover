from cover_agent.lsp_logic.utils.utils_adapt_command import adapt_test_command
from cover_agent.build_tool_adapter import *
import pytest
from typing import Optional

# Function signature we're testing:
# def BuiltToolAdapterABC.adapt_test_command(self, test_file_relative_path: str):

class TestBuiltToolAdaptTestCommandForSingleFile:
    """Test suite for rule-based test command adaptation function."""
    # Java/Maven test cases

    def test_mvn_test_basic(self):
        """Test basic Maven test command."""
        adapter = MavenAdapter("mvn verify -DfailIfNoTests=false", ".")
        result = adapter.adapt_test_command("service/CalculatorServiceTest")
        assert result == "mvn verify -DfailIfNoTests=false -Dtest=CalculatorServiceTest"

    # def test_mvn_test_with_profile(self):
    #     """Test Maven test with profile."""
    #     result = adapt_test_command(
    #         "mvn test -Pintegration", 
    #         "src/test/java/com/example/integration/DatabaseTest.java"
    #     )
    #     assert result == "mvn test -Pintegration -Dtest=DatabaseTest"
    #
    # def test_mvn_test_nested_class(self):
    #     """Test Maven test with nested test class path."""
    #     result = adapt_test_command(
    #         "mvn test", 
    #         "src/test/java/com/company/module/service/UserServiceTest.java"
    #     )
    #     assert result == "mvn test -Dtest=UserServiceTest"

    def test_mvn_with_arguments(self):
        adapter = MavenAdapter("mvn verify -DfailIfNoTests=false -Djacoco.destFile=target/lol/jacoco-run2.exec -Djacoco.dataFile=target/lol/jacoco-run2.exec -Dcustom.outputDirectory=target/lol/jacoco-run2", ".")
        result = adapter.adapt_test_command("src/test/java/com/example/calculator/controller/CalculatorControllerTest.java")

        assert result == "mvn verify -DfailIfNoTests=false -Djacoco.destFile=target/lol/jacoco-run2.exec -Djacoco.dataFile=target/lol/jacoco-run2.exec -Dcustom.outputDirectory=target/lol/jacoco-run2 -Dtest=CalculatorControllerTest"

    # Java/Gradle test cases
    # def test_gradle_test_basic(self):
    #     """Test basic Gradle test command."""
    #     result = adapt_test_command(
    #         "./gradlew test", 
    #         "src/test/java/com/example/CalculatorTest.java"
    #     )
    #     assert result == './gradlew test --tests "CalculatorTest"'
    #
    # def test_gradle_test_with_flags(self):
    #     """Test Gradle test with additional flags."""
    #     result = adapt_test_command(
    #         "./gradlew test --info", 
    #         "src/test/kotlin/com/example/ServiceTest.kt"
    #     )
    #     assert result == './gradlew test --info --tests "ServiceTest"'

    # def test_deeply_nested_test_file(self):
    #     """Test with deeply nested test file path."""
    #     result = adapt_test_command(
    #         "pytest", 
    #         "tests/unit/services/auth/providers/oauth/test_google.py"
    #     )
    #     assert result == "pytest tests/unit/services/auth/providers/oauth/test_google.py"
    #
    # def test_windows_path_separators(self):
    #     """Test with Windows-style path separators."""
    #     result = adapt_test_command(
    #         "pytest", 
    #         "tests\\unit\\test_utils.py"
    #     )
    #     # Should normalize to forward slashes or handle appropriately
    #     assert "test_utils.py" in result

    # def test_relative_vs_absolute_paths(self):
    #     """Test handling of relative vs absolute paths."""
    #     result = adapt_test_command(
    #         "pytest", 
    #         "./tests/test_relative.py"
    #     )
    #     assert result == "pytest ./tests/test_relative.py"
    #
    # def test_command_already_targeting_specific_file(self):
    #     """Test command that already targets the same specific file."""
    #     result = adapt_test_command(
    #         "pytest tests/test_specific.py", 
    #         "tests/test_specific.py"
    #     )
    #     # Should return the same command since it's already correct
    #     assert result == "pytest tests/test_specific.py"
    #
    # def test_command_with_test_name_pattern(self):
    #     """Test command with existing test name patterns."""
    #     result = adapt_test_command(
    #         "pytest -k test_login", 
    #         "tests/test_auth.py"
    #     )
    #     # Should preserve the pattern but target the specific file
    #     assert result == "pytest -k test_login tests/test_auth.py"
    #
    # # Performance and boundary tests
    # def test_very_long_command(self):
    #     """Test with very long command line."""
    #     long_flags = " ".join([f"--flag{i}=value{i}" for i in range(50)])
    #     command = f"pytest {long_flags}"
    #     result = adapt_test_command(command, "tests/test_long.py")
    #     assert result.endswith("tests/test_long.py")
    #     assert len(result) > len(command)
    #
    # def test_very_long_file_path(self):
    #     """Test with very long file path."""
    #     long_path = "/".join([f"level{i}" for i in range(20)]) + "/test_deep.py"
    #     result = adapt_test_command("pytest", long_path)
    #     assert result == f"pytest {long_path}"

    # # Python/pytest test cases
    # def test_pytest_basic(self):
    #     """Test basic pytest command."""
    #     result = adapt_test_command("pytest", "tests/test_utils.py")
    #     assert result == "pytest tests/test_utils.py"
    #
    # def test_pytest_with_flags(self):
    #     """Test pytest with various flags."""
    #     result = adapt_test_command(
    #         "pytest -v --tb=short", 
    #         "tests/test_api.py"
    #     )
    #     assert result == "pytest -v --tb=short tests/test_api.py"
    #
    # def test_pytest_with_coverage(self):
    #     """Test pytest with coverage options."""
    #     result = adapt_test_command(
    #         "pytest --cov=src --cov-report=html --cov-report=term-missing",
    #         "tests/integration/test_database.py"
    #     )
    #     assert result == "pytest --cov=src --cov-report=html --cov-report=term-missing tests/integration/test_database.py"
    #
    # def test_pytest_with_existing_file_arg(self):
    #     """Test pytest that already has a file argument - should replace it."""
    #     result = adapt_test_command(
    #         "pytest tests/", 
    #         "tests/test_specific.py"
    #     )
    #     assert result == "pytest tests/test_specific.py"
    #
    # def test_pytest_with_multiple_paths(self):
    #     """Test pytest with multiple existing paths - should replace them."""
    #     result = adapt_test_command(
    #         "pytest tests/ src/", 
    #         "tests/test_one.py"
    #     )
    #     assert result == "pytest tests/test_one.py"
    #
    # def test_python_m_pytest(self):
    #     """Test python -m pytest format."""
    #     result = adapt_test_command(
    #         "python -m pytest -v", 
    #         "tests/test_module.py"
    #     )
    #     assert result == "python -m pytest -v tests/test_module.py"

