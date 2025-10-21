from argparse import Namespace
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Tuple, Optional
from cover_agent.ai_caller import AICaller
from cover_agent.lsp_logic.utils.utils_context import (
    analyze_context,
    find_test_file_context,
    initialize_language_server,
    find_all_context,
)
from cover_agent.lsp_logic.multilspy import LanguageServer


class ContextHelper:
    def __init__(self, args: Namespace):
        self._args = args
        self._lsp: Optional[LanguageServer] = None

    @asynccontextmanager
    async def start_server(self) -> AsyncIterator[LanguageServer]:
        print("\nInitializing language server...")
        self._lsp = await initialize_language_server(self._args)
        async with self._lsp.start_server() as server:
            yield server

    async def find_test_file_context(self, test_file: Path):
        if not self._lsp:
            raise ValueError(
                "Language server not initialized. Please call start_server() first."
            )
        context_files = await find_test_file_context(self._args, self._lsp, test_file)
        return context_files

    async def find_all_context(self, file: Path) -> list[tuple[str, str, str, int, int]]:
        if not self._lsp:
            raise ValueError(
                "Language server not initialized. Please call start_server() first."
            )
        context_files = await find_all_context(self._args, self._lsp, file)
        return context_files


    async def analyze_context(
        self,
        test_file: Path,
        context_files: List[Path],
        ai_caller: AICaller,
    ) -> Tuple[Path, List[Path]]:
        if not self._lsp:
            raise ValueError(
                "Language server not initialized. Please call start_server() first."
            )
        source_file, context_files_include, context_input_token, context_output_token = await analyze_context(
            test_file, context_files, self._args, ai_caller
        )
        return source_file, context_files_include, context_input_token, context_output_token
