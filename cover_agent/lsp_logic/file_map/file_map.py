import os
from pathlib import Path
from typing import Optional

from grep_ast import TreeContext
from grep_ast.parsers import PARSERS, filename_to_lang
from tree_sitter import Node

# from pygments.lexers import guess_lexer_for_filename
# from pygments.token import Token
from tree_sitter_languages import get_language, get_parser

from cover_agent.lsp_logic.file_map.queries.get_queries import get_queries_scheme


class FileMap:
    """
    This class is used to summarize the content of a file using tree-sitter queries.
    Supported languages: C, C++, C#, elisp, elixir, go, java, javascript, ocaml, php, python, ql, ruby, rust, typescript
    """

    def __init__(
        self,
        fname_full_path: str,
        parent_context=True,
        child_context=False,
        header_max=0,
        margin=0,
        project_base_path: str = None,
    ):
        self.fname_full_path = fname_full_path
        self.project_base_path = project_base_path
        if project_base_path:
            self.fname_rel = os.path.relpath(fname_full_path, project_base_path)
        else:
            self.fname_rel = fname_full_path
        self.main_queries_path = Path(__file__).parent.parent / "queries"
        if not os.path.exists(fname_full_path):
            raise FileNotFoundError(f"File {fname_full_path} does not exist")
        with open(fname_full_path, "r") as f:
            code = f.read()
        self.code = code.rstrip("\n") + "\n"
        self.parent_context = parent_context
        self.child_context = child_context
        self.header_max = header_max
        self.margin = margin

    def summarize(self):
        query_results = self.get_query_results()
        summary_str = self.query_processing(query_results)
        return summary_str

    def render_file_summary(self, lines_of_interest: list):
        code = self.code
        fname_rel = self.fname_rel
        context = TreeContext(
            fname_rel,
            code,
            color=False,
            line_number=True,  # number the lines (1-indexed)
            parent_context=self.parent_context,
            child_context=self.child_context,
            last_line=False,
            margin=self.margin,
            mark_lois=False,
            loi_pad=0,
            header_max=self.header_max,  # max number of lines to show in a function header
            show_top_of_file_parent_scope=False,
        )

        context.lines_of_interest = set()
        context.add_lines_of_interest(lines_of_interest)
        context.add_context()
        res = context.format()
        return res

    def query_processing(self, query_results: list):
        if not query_results:
            return ""

        output = ""
        def_lines = [q["line"] for q in query_results if q["kind"] == "def"]
        output += "\n"
        output += query_results[0]["fname"] + ":\n"
        output += self.render_file_summary(def_lines)
        return output

    def get_imports(self) -> list[dict]:
        '''
            find all import lines inside current file using tree-sitter
        '''
        imports = self.get_tag("import")
        for import_line in imports:
            import_line['tag'] = 'import'
        return imports

    def get_tag(self, tag: str) -> list[dict]:
        '''
            find custom tree-sitter node with tag == tag
        '''
        fname_rel = self.fname_rel
        code = self.code
        lang = filename_to_lang(fname_rel)
        if not lang:
            return []

        try:
            language = get_language(lang)
            parser = get_parser(lang)
        except Exception as err:
            print(f"Skipping file {fname_rel}: {err}")
            return []

        query_scheme_str = get_queries_scheme(lang)
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the queries
        query = language.query(query_scheme_str)
        captures = list(query.captures(tree.root_node))

        results = []
        for node, capture_tag in captures:
            if capture_tag == tag:
                result = dict(
                    fname=fname_rel,
                    name=node.text.decode("utf-8"),
                    tag=tag,
                    start_line=node.start_point[0],
                    start_column=node.start_point[1],  # in order to find indentation or test file
                    end_line=node.end_point[0],
                )
                results.append(result)

        # print("results are: ", results)
        return results

    def get_functions(self) -> list[dict]:
        '''
            find all unit tests in current file using tree-sitter
        '''
        return self.get_tag("test")

    def get_range(self, line: int) -> Optional[tuple[int, int]]:
        """
        Finds all enclosing structural ranges (like functions or classes) for a given line number in the file.
        This method uses tree-sitter to parse the file and identify all structural elements
        (based on the language's query scheme). It then checks which of these elements
        contain the specified line number and returns a list of their start and end lines.
        Args:
        line (int): The 0-indexed line number to find the enclosing ranges for.

        Returns:
            Optional[tuple[int, int]]: A single (start_line, end_line) tuple for the smallest
                                    enclosing block, or None if no enclosing block is found.
        """
        fname_rel = self.fname_rel
        code = self.code
        lang = filename_to_lang(fname_rel)
        if not lang:
            return

        try:
            # Get the tree-sitter parser and language for the file's language.
            language = get_language(lang)
            parser = get_parser(lang)
        except Exception as err:
            print(f"Skipping file {fname_rel}: {err}")
            return

        # Load the tree-sitter queries for the language.
        query_scheme_str = get_queries_scheme(lang)
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the queries to get all captures (tagged nodes in the syntax tree).
        query = language.query(query_scheme_str)
        captures: list[tuple[Node, str]] = list(query.captures(tree.root_node))
        potential = []
        # Iterate through all the captured nodes.
        for capture in captures:
            start_line: int = capture[0].start_point[0]
            end_line: int = capture[0].end_point[0]
            is_method: bool = capture[1].endswith("method")
            # Check if the given line is within the start and end lines of the captured node.
            # We also ensure the node spans more than one line to filter out single-line constructs.
            if (line <= end_line and line >= start_line and start_line != end_line):# and is_method):
                potential.append((start_line, end_line))

        # print('ranges: ', potential)
        if not potential:
            return None

        # Find and return the smallest range (smallest difference between end and start)
        smallest_range = min(potential, key=lambda r: r[1] - r[0])
        return smallest_range

    def get_query_results_in_range(self, start_line: int = 0, end_line: int = -1) -> tuple[list[dict], list] | None:
        '''
            get tree-sitter query results from a certain range
        '''
        fname_rel = self.fname_rel
        code = self.code
        # code_sub_section = "\n".join(code.split("\n")[start_line:end_line])
        # print("code sub section: ", code_sub_section)
        lang = filename_to_lang(fname_rel)
        if not lang:
            return

        try:
            language = get_language(lang)
            parser = get_parser(lang)
        except Exception as err:
            print(f"Skipping file {fname_rel}: {err}")
            return

        query_scheme_str = get_queries_scheme(lang)
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the queries
        query = language.query(query_scheme_str)
        captures: tuple[Node, str] = list(query.captures(tree.root_node))

        # Parse the results into a list of "def" and "ref" tags
        visited_set = set()
        results = []
        for node, tag in captures:
            # filter based on range
            if node.start_point[0] > start_line and (node.end_point[0] < end_line or end_line == -1):
                if tag.startswith("name.definition."):
                    kind = "def"
                elif tag.startswith("name.reference."):
                    kind = "ref"
                elif tag == "dot.class":
                    kind = "ref"
                else:
                    continue

                visited_set.add(kind)
                result = dict(
                    fname=fname_rel,
                    name=node.text.decode("utf-8"),
                    kind=kind,
                    tag=tag,
                    column=node.start_point[1],
                    start=node.start_point[0],
                    end=node.end_point[0],
                )
                results.append(result)

        if "ref" in visited_set:
            return results, captures
        if "def" not in visited_set:
            return results, captures

        return results, captures

    def get_query_results(self) -> tuple[list[dict], list]:
        fname_rel = self.fname_rel
        code = self.code
        # print("=========================")
        # print("code is: ", code.split('\n'))
        # print("=========================")
        lang = filename_to_lang(fname_rel)
        if not lang:
            return

        try:
            language = get_language(lang)
            parser = get_parser(lang)
        except Exception as err:
            print(f"Skipping file {fname_rel}: {err}")
            return

        query_scheme_str = get_queries_scheme(lang)
        tree = parser.parse(bytes(code, "utf-8"))

        # Run the queries
        query = language.query(query_scheme_str)
        captures = list(query.captures(tree.root_node))

        # Parse the results into a list of "def" and "ref" tags
        visited_set = set()
        results = []
        for node, tag in captures:
            if tag.startswith("name.definition."):
                kind = "def"
            elif tag.startswith("name.reference."):
                kind = "ref"
            else:
                continue

            visited_set.add(kind)
            result = dict(
                fname=fname_rel,
                name=node.text.decode("utf-8"),
                tag=tag,
                kind=kind,
                line=node.start_point[0],
            )
            results.append(result)

        if "ref" in visited_set:
            return results, captures
        if "def" not in visited_set:
            return results, captures

        ## currently we are interested only in defs
        # # We saw defs, without any refs
        # # Some files only provide defs (cpp, for example)
        # # Use pygments to backfill refs
        # try:
        #     lexer = guess_lexer_for_filename(fname, code)
        # except Exception:
        #     return
        #
        # tokens = list(lexer.get_tokens(code))
        # tokens = [token[1] for token in tokens if token[0] in Token.Name]
        #
        # for t in tokens:
        #     result = dict(
        #         fname=fname,
        #         name=t,
        #         kind="ref",
        #         line=-1,
        #     )
        #     results.append(result)
        return results, captures # results from functions are rarely used anywhere, maybe remove?? 
