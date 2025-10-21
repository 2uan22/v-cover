import os
import argparse
from time import sleep
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from cover_agent.lsp_logic.file_map.file_map import FileMap
from cover_agent.lsp_logic.multilspy import LanguageServer
from cover_agent.lsp_logic.multilspy.multilspy_config import MultilspyConfig
from cover_agent.lsp_logic.multilspy.multilspy_logger import MultilspyLogger

from cover_agent.settings.config_loader import get_settings
from cover_agent.utils import load_yaml


def find_java_primary_file(test_file, project_root):
    """
    Find the primary source file for a Java test file based on naming conventions.

    Args:
        test_file: Path to the test file
        project_root: Root directory of the project

    Returns:
        Path to the primary source file if found, None otherwise
    """
    test_filename = os.path.basename(test_file)
    test_dir = os.path.dirname(test_file)

    # Common Java test naming patterns
    test_suffixes = ["Test", "Tests", "TestCase", "IT", "IntegrationTest"]

    # Try to find the source file by removing test suffixes
    for suffix in test_suffixes:
        if test_filename.endswith(suffix + ".java"):
            source_filename = test_filename[: -len(suffix + ".java")] + ".java"

            # Look in common source locations relative to test location
            possible_paths = []

            # If test is in src/test/java, look in src/main/java
            if "src/test/java" in test_file:
                source_path = test_file.replace(
                    "src/test/java", "src/main/java"
                ).replace(test_filename, source_filename)
                possible_paths.append(source_path)

            # Look in the same package structure but different source roots
            rel_path = os.path.relpath(test_dir, project_root)
            for src_dir in ["src/main/java", "src/java", "src"]:
                if src_dir in rel_path:
                    continue
                potential_path = os.path.join(
                    project_root,
                    src_dir,
                    rel_path.replace("src/test/java", "")
                    .replace("test", "")
                    .strip("/"),
                    source_filename,
                )
                possible_paths.append(potential_path)

            # Also check in the same directory (for simple projects)
            possible_paths.append(os.path.join(test_dir, source_filename))

            # Check if any of the possible paths exist
            for path in possible_paths:
                if os.path.exists(path):
                    return path

    return None


async def analyze_context(test_file, context_files, args, ai_caller) -> (str, str, int, int):
    """
    # we now want to analyze the test file against the source files and determine several things:
    # 1. If this test file is a unit test file
    # 2. Which of the context files can be seen as the main source file for this test file, for which we want to increase coverage
    # 3. Set all other context files as additional 'included_files' for the CoverAgent
    """
    source_file = None
    context_files_include = context_files
    prompt_token_count = 0
    response_token_count = 0
    try:
        test_file_rel_str = os.path.relpath(test_file, args.project_root)
        context_files_rel_filtered_list_str = ""
        for file in context_files:
            context_files_rel_filtered_list_str += (
                f"`{os.path.relpath(file, args.project_root)}`\n"
            )
        variables = {
            "language": args.project_language,
            "test_file_name_rel": test_file_rel_str,
            "test_file_content": open(test_file, "r").read(),
            "context_files_names_rel": context_files_rel_filtered_list_str,
        }
        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(
            get_settings().analyze_test_against_context.system
        ).render(variables)
        user_prompt = environment.from_string(
            get_settings().analyze_test_against_context.user
        ).render(variables)
        # print("0000000000000000000000000000000000000000000000000000000000000000000000")
        # print(user_prompt)
        # print("0000000000000000000000000000000000000000000000000000000000000000000000")
        response, prompt_token_count, response_token_count = await ai_caller.call_model(
            prompt={"system": system_prompt, "user": user_prompt}, stream=False
        )
        response_dict = load_yaml(response)
        if int(response_dict.get("is_this_a_unit_test", 0)) == 1:
        # if int(response_dict.get("is_unit_test", 0)) == 1:
            source_file_rel = response_dict.get("main_file", "").strip().strip("`")
            source_file = os.path.join(args.project_root, source_file_rel)
            for file in context_files:
                file_rel = os.path.relpath(file, args.project_root)
                if file_rel == source_file_rel:
                    context_files_include = [f for f in context_files if f != file]

        if source_file:
            print(
                f"Test file: `{test_file}`,\nis a unit test file for source file: `{source_file}`"
            )
        else:
            print(f"Test file: `{test_file}` is not a unit test file")
    except Exception as e:
        print(f"Error while analyzing test file {test_file} against context files: {e}")

    return source_file, context_files_include, prompt_token_count, response_token_count

async def find_all_context(args: argparse.Namespace, lsp: LanguageServer, test_file: Path) -> list[tuple[str, str, str, int, int]]:
    '''
    find and return all context files using tree-sitter and LSP
    Returns list of tuple containing:
        primary_file (str): The primary source file for the test file, or the file under test
        name (str): Name of the function, method or class that is referenced in the test file, mostly for debugging
        scope (str): Name of the scope of the symbol, e.g. CalculatorService has a scope of class
        start_line (int): Start line of the code block
        end_line (int): End line of the code block
    '''
    context_files = [] #set()
    # visited = set()

    if args.project_language == "java" and test_file.endswith(".java"):
        potential_primary = find_java_primary_file(test_file, args.project_root)
        if potential_primary:
            primary_file = Path(potential_primary).resolve()

            # default to name being class name and start and end line as the start and line of file
            context_file = (str(primary_file), os.path.basename(primary_file).split('.')[0], 'class', 0, -1) 
            context_files.append(context_file)
            await _recursive_search(0, args, potential_primary, context_files, lsp)

    await _recursive_search(0, args, test_file, context_files, lsp)

    return context_files


async def _recursive_search(call_num: int, args: argparse.Namespace, file: Path, dependency_set: list[tuple], lsp: LanguageServer, visited: set[tuple] = set(), range: tuple[int, int] = (0, -1)):
    """
    Recursively searches for the context of a given file or code range.
    
    This function is the core of the context discovery process. It starts with a
    file and finds all code symbols within it. It then uses the Language Server
    Protocol (LSP) to find the definitions of those symbols, which might be in
    other files. It then recursively calls itself on those new files to find
    their dependencies, up to a fixed depth.

    Args:
        call_num (int): The current recursion depth, used to prevent infinite loops.
        args (argparse.Namespace): The application's command-line arguments.
        file (Path): The file to analyze in the current recursion step.
        dependency_set (list[tuple]): The list where result tuples are accumulated.
                        This list is modified in place by the function.
        lsp (LanguageServer): The active LSP client.
        visited (set[tuple]): A set to track found dependencies to avoid re-processing
                        and infinite recursion.
        range (tuple[int, int]): The (start_line, end_line) range within the file
                        to analyze. Defaults to the entire file.
    """

    # 1. Stop recursion if the maximum depth is reached.
    if call_num >= 5:
        return
    # print("call number: ", call_num)
    # print("+++++")
    # print(dependency_set)
    call_num = call_num + 1

    # find symbols in range
    file = Path(file)
    absolute_project_dir = Path(args.project_root).resolve()
    fname_full_path = absolute_project_dir / file

    # 2. Use FileMap and tree-sitter to find all symbols within the current file and range
    fname_summary = FileMap(
        fname_full_path,
        parent_context=False,
        child_context=False,
        header_max=0,
        project_base_path=args.project_root,
    )
    query_results, captures = fname_summary.get_query_results_in_range(range[0], range[1])
    imports = fname_summary.get_imports()
    if imports:
        # All imports are from the same file, so we can get the fname from the first one.
        file_path = Path(imports[0]['fname']).resolve()
        
        # The get_imports() list is sorted, so find the min start and max end lines.
        start_line = imports[0]['start_line']
        end_line = imports[-1]['end_line']
        
        # Create a single dependency entry for the entire import block.
        dependency_set.append((str(file_path), "import block", "import", start_line, end_line))
    # print("query_results, captures = ", len(query_results), len(captures))
    # print("======")
    # print("query results are found: ", query_results)
    # print("captures: ", captures)

    # 3. Use LSP to perform a "go to definition" lookup on the found symbols.
    # This returns a set of (file_path, symbol_name, symbol_scope, definition_start_line) tuples.
    context_files_and_lines: set[tuple[str, str, str, int]] = await lsp.get_direct_context_file_and_line(
        query_results, captures, args.project_language, args.project_root, file
    )
    # print("========context_files_and_lines: ==============")
    # print(context_files_and_lines)

    # print("     ===================")
    # print("context files found from query results: ")
    # print(context_files_and_lines)
    # print("     ===================")
    # 4. Process each definition (dependency) found by the LSP.
    for context_file_and_line in context_files_and_lines:
        context_file, symbol_name, symbol_scope, line = context_file_and_line
        # print("^^^^^^^^^^^^^^^^^^")
        # print(context_file_and_line)
        context_file = Path(context_file).resolve()
        args.project_root = Path(args.project_root).resolve()
        # print("context_file: ", context_file)
        # print("args.project_root: ", args.project_root)
        # print("context file being relative to args.project_root: ", context_file.is_relative_to(args.project_root))

        # print("context file being relative could be: ", os.path.commonpath([args.project_root, context_file]) == args.project_root)

        if not Path(context_file).is_relative_to(Path(args.project_root)):
            continue
        try:
            fm = FileMap(
                context_file,
                parent_context=False,
                child_context=False,
                header_max=0,
                project_base_path=args.project_root,
            )
        except FileNotFoundError as e:
            continue

        # 5. Find the full range (e.g., the entire function/class body) of the dependency. 
        # This gets the smallest range.
        context_range: Optional[tuple[int, int]] = fm.get_range(line)
        # If no enclosing range is found, skip this dependency.
        if not context_range:
            continue

        # 6. Create the dependency tuple. We convert `context_file` back to a string
        dependency: tuple = (str(context_file), symbol_name, symbol_scope, context_range[0], context_range[1])
        # print(f"found dependency {dependency}")
        # if dependency in visited: 
        #     print(f"dependency {dependency} already found inside visited set {visited}")
        if dependency not in visited:
            dependency_set.append(dependency)
            visited.add(dependency)

            # 7. Recurse: Analyze the newly found dependency for its own context.
            await _recursive_search(call_num, args, context_file, dependency_set, lsp, visited, context_range)



# not used
async def find_test_file_context(args: argparse.Namespace, lsp: LanguageServer, test_file: Path) -> list[dict]:
    '''
        function to find all context files recursively, and return list of dictionary containing file path, start line and end line.
    '''
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, args.project_root)
        absolute_file = str(os.path.abspath(args.project_root))
        cwd = os.getcwd()

        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=args.project_root,
        )
        results = fname_summary.get_query_results_in_range()
        # print("____________")
        # print("results: ", results)
        query_results, captures = results
        # print("query results: ", query_results)
        # print('types: ', results.__class__.__module__)
        # print('captures:', captures[0][0].__class__)

        context_files, context_symbols = await lsp.get_direct_context(
            captures, args.project_language, args.project_root, rel_file
        )
        # print("\n".join([f"{context_files} for symbol {list(context_symbols)[i]}" for i, context_file in enumerate(list(context_files))]))
        # print("context_symbols: ", context_symbols)
        # filter empty files and files not in current working directory
        context_files_filtered = []
        for file in context_files:
            if cwd in os.path.abspath(file):
                with open(file, "r") as f:
                    if f.read().strip() and cwd in absolute_file:
                        context_files_filtered.append(file)
        context_files = context_files_filtered
        # print("context files FILTERED: ", context_files_filtered)

        # For Java files, try to find the primary source file
        if args.project_language == "java" and test_file.endswith(".java"):
            potential_primary = find_java_primary_file(test_file, args.project_root)
            if potential_primary:
                primary_file = potential_primary
                context_files.append(primary_file)

        # print("Getting context done.")
    except Exception as e:
        print(f"Error while getting context for test file {test_file}: {e}")
        context_files = []

    return context_files

# not used
async def find_test_file_direct_context(args: argparse.Namespace, lsp: LanguageServer, test_file: Path) -> list[str]:
    '''
        get the direct context of a test file, doesn't recursively find dependencies
    '''
    try:
        target_file = test_file
        rel_file = os.path.relpath(target_file, args.project_root)
        absolute_file = str(os.path.abspath(args.project_root))
        cwd = os.getcwd()

        fname_summary = FileMap(
            target_file,
            parent_context=False,
            child_context=False,
            header_max=0,
            project_base_path=args.project_root,
        )
        query_results, captures = fname_summary.get_query_results()

        context_files, context_symbols = await lsp.get_direct_context(
            captures, args.project_language, args.project_root, rel_file
        )
        # filter empty files
        context_files_filtered = []
        for file in context_files:
            with open(file, "r") as f:
                if f.read().strip():
                    context_files_filtered.append(file)
        context_files = context_files_filtered

        # For Java files, try to find the primary source file
        if args.project_language == "java" and test_file.endswith(".java"):
            potential_primary = find_java_primary_file(test_file, args.project_root)
            if potential_primary:
                primary_file = potential_primary
                context_files.append(primary_file)

        # print("Getting context done.")
    except Exception as e:
        print(f"Error while getting context for test file {test_file}: {e}")
        context_files = []

    return context_files


async def initialize_language_server(args):
    logger = MultilspyLogger()
    config = MultilspyConfig.from_dict({"code_language": args.project_language})
    if args.project_language == "python" or args.project_language == "java":
        lsp = LanguageServer.create(config, logger, args.project_root)
        sleep(0.1)
        return lsp
    else:
        raise NotImplementedError(
            "Unsupported language: {}".format(args.project_language)
        )
