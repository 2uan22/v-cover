import os
import re
from pathlib import Path

def adapt_test_command(command: str, file_path: str) -> str | None:
    """
    Takes a test command and a file path, and adapts the command to run
    only the specified test file.

    Args:
        command (str): The original test command.
        file_path (str): The absolute or relative path to the single test file.

    Returns:
        str: The adapted test command or None if not any of the testing framework available.
    """
    command = command.strip()
    
    # The order matters here. Check for more specific commands first.
    if "gradle" in command or "gradlew" in command:
        return _adapt_for_gradle(command, file_path)
    if "mvn" in command or "mvnw" in command:
        return _adapt_for_maven(command, file_path)
    if "pytest" in command:
        return _adapt_for_pytest(command, file_path)
    if "jest" in command:
        return _adapt_for_jest(command, file_path)
    if "mocha" in command:
        return _adapt_for_mocha(command, file_path)
    if "npm test" in command or "npm run test" in command or "yarn test" in command or "pnpm test" in command:
        return _adapt_for_npm_yarn(command, file_path)
    if "go test" in command:
        return _adapt_for_go(command, file_path)
    if "dotnet test" in command:
        return _adapt_for_dotnet(command, file_path)
    if "rspec" in command:
        return _adapt_for_rspec(command, file_path)
    if "phpunit" in command:
        return _adapt_for_phpunit(command, file_path)
    if "cargo test" in command:
        return _adapt_for_cargo(command, file_path)
    if "unittest" in command:
        return _adapt_for_unittest(command, file_path)

    return None


def _adapt_for_pytest(command: str, file_path: str) -> str:
    """
    Adapts a pytest command. It replaces existing file/directory targets.
    Example: `pytest --cov tests/` -> `pytest --cov path/to/test.py`
    """
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take values
        if arg in ['-k', '--tb', '--cov', '--cov-report', '--rootdir', '--confcutdir']:
            new_args.append(arg)
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
            continue
            
        # Skip existing test paths (but keep flags and their values)
        if (not arg.startswith('-') and 
            (os.path.exists(arg) or '::' in arg or 
             arg.endswith('.py') or '/' in arg)):
            continue
            
        new_args.append(arg)

    new_args.append(file_path)
    return  " ".join(new_args)


def _adapt_for_jest(command: str, file_path: str) -> str:
    """
    Adapts a Jest command by appending the file path.
    Example: `jest --coverage --verbose` -> `jest --coverage --verbose path/to/test.js`
    """
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take values
        if arg in ['--config', '--testNamePattern', '--testPathPattern', '--maxWorkers', '--testTimeout']:
            new_args.append(arg)
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
            continue
            
        # Skip existing test paths
        if (not arg.startswith('-') and 
            (os.path.exists(arg) or arg.endswith(('.js', '.ts', '.jsx', '.tsx')) or 
             '/' in arg or '*' in arg)):
            continue
            
        new_args.append(arg)

    new_args.append(file_path)
    return " ".join(new_args)


def _adapt_for_mocha(command: str, file_path: str) -> str:
    """
    Adapts a Mocha command by replacing test directory with specific file.
    Example: `mocha --recursive test/` -> `mocha test/unit/test.js`
    """
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take values
        if arg in ['--reporter', '--timeout', '--grep', '--require']:
            new_args.append(arg)
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
            continue
            
        # Skip --recursive as it's not needed for single files
        if arg == '--recursive':
            continue
            
        # Skip existing test paths
        if (not arg.startswith('-') and 
            (os.path.exists(arg) or arg.endswith(('.js', '.ts', '.coffee')) or 
             '/' in arg)):
            continue
            
        new_args.append(arg)

    new_args.append(file_path)
    return " ".join(new_args)


def _adapt_for_npm_yarn(command: str, file_path: str) -> str:
    """
    Adapts npm/yarn/pnpm test commands. Assumes the underlying test runner
    accepts a file path after a '--' separator.
    Example: `npm test` -> `npm test -- path/to/test.js`
    """
    if "--" in command:
        # Replace existing paths after --
        parts = command.split("--")
        base_command = parts[0].strip()
        return f"{base_command} -- {file_path}"
    return f"{command} -- {file_path}"


def _adapt_for_go(command: str, file_path: str) -> str:
    """
    Adapts a Go test command. Go operates on packages, so we provide
    the directory containing the test file.
    Example: `go test ./...` -> `go test ./path/to/package/`
    """
    package_dir = os.path.dirname(file_path) or "."
    
    args = command.split()
    new_args = []
    
    for arg in args:
        # Replace broad package specifiers
        if arg in ['./...', './all', '...']:
            continue
        # Skip existing package paths
        if (not arg.startswith('-') and 
            (arg.startswith('./') or arg.startswith('../') or 
             '/' in arg) and arg != 'go' and arg != 'test'):
            continue
        new_args.append(arg)

    # Add the specific package directory
    new_args.append(f"./{package_dir}")
    return " ".join(new_args)


def _adapt_for_maven(command: str, file_path: str) -> str:
    """
    Adapts a Maven command using the -Dtest flag.
    Example: `mvn test` -> `mvn test -Dtest=TestClassName`
    """
    # Extract class name from file path
    file_name = os.path.basename(file_path)
    class_name = os.path.splitext(file_name)[0]
    
    # Remove existing -Dtest arguments
    args = command.split()
    new_args = []
    
    for arg in args:
        if arg.startswith('-Dtest='):
            continue
        new_args.append(arg)
    
    new_args.append(f"-Dtest={class_name}")
    return " ".join(new_args)


def _adapt_for_gradle(command: str, file_path: str) -> str:
    """
    Adapts a Gradle command using the --tests filter.
    Example: `gradle test` -> `gradle test --tests "TestClassName"`
    """
    # Extract class name from file path
    file_name = os.path.basename(file_path)
    class_name = os.path.splitext(file_name)[0]
    
    # Remove existing --tests arguments
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == '--tests':
            skip_next = True
            continue
        new_args.append(arg)
    
    new_args.extend(['--tests', f'"{class_name}"'])
    return " ".join(new_args)


def _adapt_for_dotnet(command: str, file_path: str) -> str:
    """
    Adapts a dotnet test command using --filter.
    Example: `dotnet test` -> `dotnet test --filter ClassName=TestClass`
    """
    file_name = os.path.basename(file_path)
    class_name = os.path.splitext(file_name)[0]
    
    # Remove existing --filter arguments
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg == '--filter':
            skip_next = True
            continue
        new_args.append(arg)
    
    new_args.extend(['--filter', f'ClassName={class_name}'])
    return " ".join(new_args)


def _adapt_for_rspec(command: str, file_path: str) -> str:
    """
    Adapts an RSpec command by replacing spec directories with specific file.
    Example: `rspec --format doc spec/` -> `rspec --format doc spec/models/user_spec.rb`
    """
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take values
        if arg in ['--format', '--require', '--pattern']:
            new_args.append(arg)
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
            continue
            
        # Skip existing spec paths
        if (not arg.startswith('-') and 
            (os.path.exists(arg) or arg.endswith('_spec.rb') or 
             arg.startswith('spec/') or '/' in arg)):
            continue
            
        new_args.append(arg)

    new_args.append(file_path)
    return " ".join(new_args)


def _adapt_for_phpunit(command: str, file_path: str) -> str:
    """
    Adapts a PHPUnit command by appending the test file.
    Example: `phpunit --coverage-html coverage` -> `phpunit --coverage-html coverage tests/UserTest.php`
    """
    args = command.split()
    new_args = []
    skip_next = False
    
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take values
        if arg in ['--coverage-html', '--coverage-xml', '--log-junit', '--configuration']:
            new_args.append(arg)
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                skip_next = True
            continue
            
        # Skip existing test paths
        if (not arg.startswith('-') and 
            (os.path.exists(arg) or arg.endswith('Test.php') or 
             'tests/' in arg or '/' in arg)):
            continue
            
        new_args.append(arg)

    new_args.append(file_path)
    return " ".join(new_args)


def _adapt_for_cargo(command: str, file_path: str) -> str:
    """
    Adapts a Cargo test command. For integration tests, we use --test flag.
    Example: `cargo test` -> `cargo test --test integration_test`
    """
    # Extract test name from file path
    file_name = os.path.basename(file_path)
    test_name = os.path.splitext(file_name)[0]
    
    # Check if it's an integration test (in tests/ directory)
    if 'tests/' in file_path and not file_path.endswith('mod.rs'):
        args = command.split()
        new_args = []
        
        # Remove existing --test arguments
        skip_next = False
        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if arg == '--test':
                skip_next = True
                continue
            new_args.append(arg)
        
        new_args.extend(['--test', test_name])
        return " ".join(new_args)
    else:
        # For unit tests, just run cargo test with the module name
        return f"{command} {test_name}"


def _adapt_for_unittest(command: str, file_path: str) -> str:
    """
    Adapts a Python unittest command.
    Example: `python -m unittest` -> `python -m unittest tests.test_user.TestUser`
    """
    # Convert file path to module path
    module_path = file_path.replace('/', '.').replace('\\', '.')
    if module_path.endswith('.py'):
        module_path = module_path[:-3]
    
    return f"{command} {module_path}"

# def adapt_test_command(test_command: str, test_file_relative_path: str) -> str | None:
#     new_command_line = None
#     if "pytest" in test_command:
#         new_command_line = adapt_pytest_command(test_command, test_file_relative_path)
#
#     return new_command_line

# def adapt_pytest_command(test_command: str, test_file_relative_path: str) -> str | None:
#     try:
#         # Modify pytest command to target a single test file
#         ind1 = test_command.index("pytest")
#         print(ind1)
#         ind2 = test_command[ind1:].index("--")
#         print(ind2)
#         print(test_command[ind1+ind2:])
#         return f"{test_command[:ind1]}pytest {test_file_relative_path} {test_command[ind1 + ind2:]}"
#     except ValueError:
#         self.logger.error(f"Failed to adapt test command for running a single test: {test_command}")
#
#     return None
