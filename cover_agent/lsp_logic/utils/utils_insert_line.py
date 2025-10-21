import os
from collections import Counter

from cover_agent.lsp_logic.file_map.file_map import FileMap


def find_unit_test_insert_line(language: str, project_root: str, test_file: str) -> int | None:
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

        last_line: int = results[-1]['end_line']
        for result in results:
            if result['end_line'] + 1 > last_line and 'test' in result['name'].lower():
                last_line = result['end_line']

        return last_line + 1
    except Exception as e:
        print(
            f"Error while getting indentation, falling back to using LLM maybe??: {e}"
        )
        return None
    # with open(test_file, 'r') as f:
    #     content = f.read()
    #     file_len = len(content.split("\n"))
    # return file_len # defaults to last line in file

def find_import_insert_line(language: str, project_root: str, test_file: str) -> int | None:
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
        results = fname_summary.get_imports()

        return results[-1]['start_line']
    except Exception as e:
        print(
            f"Error while getting indentation, falling back to using LLM maybe??: {e}"
        )
        return None

