import os
import argparse
from collections import Counter

from cover_agent.lsp_logic.file_map.file_map import FileMap


def find_indentation_amount(language: str, project_root: str, test_file: str) -> int | None:
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, project_root)

        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=project_root,
        )
        # query_results, captures =
        results = fname_summary.get_functions()

        number_of_tests = len(results)
        indentation_counter = Counter([result["start_column"] for result in results])
        test_headers_indentation = indentation_counter.most_common(1)[0][0]
        # print(f"test_headers_indentation = {test_headers_indentation}")
        # print(f"number_of_tests = {number_of_tests}")
        return test_headers_indentation

        # print("results from treesitter: ", results)
    except Exception as e:
        print(
            f"Error while getting indentation, falling back to using LLM maybe??: {e}"
        )
        return 4 

def find_number_of_tests(language: str, project_root: str, test_file: str) -> int | None:
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, project_root)

        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=project_root,
        )
        results = fname_summary.get_functions()

        # very primative searching for 'test' string inside function
        number_of_tests = 0
        print('results:', results)
        for result in results:
            print("---")
            print(result)
            if "test" in result['name'].lower():
                number_of_tests += 1

        return number_of_tests 

    except Exception as e:
        print(
            f"Error while getting indentation, falling back to using LLM maybe??: {e}"
        )
        return None

def find_framework_from_imports(imports: list[str], language: str) -> str:
    """
        Determines the testing framework by pattern matching against import statements
        for a specific language.

        imports: A list of import statements from the test file.
        Args:
        language: The programming language of the test file.

        Returns:
        The name of the testing framework, or "unknown" if it can't be determined.
    """
    framework_patterns = {
        "python": {
            "pytest": ["pytest"],
            "unittest": ["unittest"],
        },
        "java": {
            "junit": ["org.junit.", "org.junit.jupiter.api."],
            "testng": ["org.testng."],
        },
        "javascript": {
            "jest": ["@jest/globals"],
            "mocha": ["mocha"],
            "vitest": ["vitest"],
        },
        "typescript": {
            "jest": ["@jest/globals"],
            "mocha": ["mocha"],
            "vitest": ["vitest"],
        },
        "go": {
            "testify": ["github.com/stretchr/testify"],
        },
        "c#": {
            "xunit": ["Xunit"],
            "nunit": ["NUnit.Framework"],
        },
        "ruby": {
            "minitest": ["minitest/autorun"],
            "rspec": ["rspec"],
        },
    }

    language = language.lower()
    if language in framework_patterns:
        for framework, patterns in framework_patterns[language].items():
            for pattern in patterns:
                for imp in imports:
                    if pattern in imp:
                        return framework

    return "Unknown"


def find_framework(language: str, project_root: str, test_file: str) -> str:
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, project_root)

        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=project_root,
        )
        imports_results = fname_summary.get_imports()
        
        imports = []
        for import_statement in imports_results:
            imports.append(import_statement['name'])

        return find_framework_from_imports(imports, language)
    except Exception as e:
        print(f"Error while getting framework, falling back to using LLM maybe??: {e}")
        # TODO: fallback to LLM here

    return "Unknown"

