import os
import re
from pathlib import Path
from typing import List, Set, Dict

class TestableFileFinder:
    """Identifies testable files based on language-specific patterns."""
    
    # Define testable patterns for different languages
    TESTABLE_PATTERNS: Dict[str, Dict[str, List[str]]] = {
        "java": {
            "include_patterns": [
                # r".*\.java$",
                r".*Controller\.java$",
                r".*Service\.java$",
                # r".*Mapper\.java$",
                r".*Utils?\.java$",
                r".*Helper\.java$",
                r".*Manager\.java$",
                r".*Handler\.java$",
                r".*Processor\.java$",
                r".*Validator\.java$",
                r".*Converter\.java$",
                r".*Factory\.java$",
                # r".*Builder\.java$",
                r".*Adapter\.java$",
            ],
            "exclude_patterns": [
                r".*Application\.java$",
                r".*Repository\.java$",
                r".*Entity\.java$",
                r".*Entities\.java$",
                r".*Model\.java$",
                r".*DTO\.java$",
                r".*Dto\.java$",
                r".*Constants?\.java$",
                r".*Config\.java$",
                r".*Configuration\.java$",
                r".*Enum\.java$",
                r".*Exception\.java$",
                r".*Interface\.java$",
                r".*Abstract.*\.java$",
                r".*Test\.java$",
                r".*Tests\.java$",
                r".*Spec\.java$",
            ]
        },
        "python": {
            "include_patterns": [
                r".*\.py$",  # All Python files by default
            ],
            "exclude_patterns": [
                r"__pycache__",
                r".*test.*\.py$",
                r".*_test\.py$",
                r"test_.*\.py$",
                r".*conftest\.py$",
                r"setup\.py$",
                r"__init__\.py$",
                r".*constants?\.py$",
                r".*config\.py$",
                r".*settings\.py$",
                r".*migrations?/.*\.py$",
                r".*\.pyi$",  # Type stub files
            ]
        },
        "javascript": {
            "include_patterns": [
                r".*\.js$",
                r".*\.jsx$",
            ],
            "exclude_patterns": [
                r".*\.test\.js$",
                r".*\.spec\.js$",
                r".*\.test\.jsx$",
                r".*\.spec\.jsx$",
                r".*\.config\.js$",
                r".*\.min\.js$",
                r"node_modules/",
                r"dist/",
                r"build/",
                r"coverage/",
                r".*\.d\.ts$",
            ]
        },
        "typescript": {
            "include_patterns": [
                r".*\.ts$",
                r".*\.tsx$",
            ],
            "exclude_patterns": [
                r".*\.test\.ts$",
                r".*\.spec\.ts$",
                r".*\.test\.tsx$",
                r".*\.spec\.tsx$",
                r".*\.d\.ts$",
                r".*\.config\.ts$",
                r"node_modules/",
                r"dist/",
                r"build/",
                r"coverage/",
                r".*interface\.ts$",
                r".*types?\.ts$",
                r".*constants?\.ts$",
                r".*enum\.ts$",
            ]
        },
        "csharp": {
            "include_patterns": [
                r".*Controller\.cs$",
                r".*Service\.cs$",
                r".*Repository\.cs$",
                r".*Manager\.cs$",
                r".*Handler\.cs$",
                r".*Helper\.cs$",
                r".*Utils?\.cs$",
                r".*Validator\.cs$",
                r".*Processor\.cs$",
            ],
            "exclude_patterns": [
                r".*Test\.cs$",
                r".*Tests\.cs$",
                r".*Spec\.cs$",
                r".*Model\.cs$",
                r".*Entity\.cs$",
                r".*Dto\.cs$",
                r".*Constants?\.cs$",
                r".*Config\.cs$",
                r".*Enum\.cs$",
                r".*Interface\.cs$",
                r".*Abstract.*\.cs$",
            ]
        },
        "go": {
            "include_patterns": [
                r".*\.go$",
            ],
            "exclude_patterns": [
                r".*_test\.go$",
                r".*\.pb\.go$",  # Protocol buffer generated files
                r"vendor/",
                r".*mock.*\.go$",
            ]
        },
        "ruby": {
            "include_patterns": [
                r".*\.rb$",
            ],
            "exclude_patterns": [
                r".*_spec\.rb$",
                r".*_test\.rb$",
                r"spec/",
                r"test/",
                r"config/",
                r"db/migrate/",
            ]
        }
    }
    
    def __init__(self, project_root: str, language: str):
        self.project_root = Path(project_root)
        self.language = language.lower()
        
    def find_testable_files(self) -> List[str]:
        """Find all testable files in the project based on language patterns."""
        if self.language not in self.TESTABLE_PATTERNS:
            raise ValueError(f"Unsupported language: {self.language}")
        
        patterns = self.TESTABLE_PATTERNS[self.language]
        include_patterns = [re.compile(p) for p in patterns["include_patterns"]]
        exclude_patterns = [re.compile(p) for p in patterns["exclude_patterns"]]
        
        testable_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = str(file_path.relative_to(self.project_root))
                
                # Check if file matches include patterns
                if any(pattern.match(relative_path) for pattern in include_patterns):
                    # Check if file doesn't match exclude patterns
                    if not any(pattern.match(relative_path) for pattern in exclude_patterns):
                        testable_files.append(str(file_path))
        
        return sorted(testable_files)
    
    def filter_files_without_tests(self, testable_files: List[str], test_files: List[str]) -> List[str]:
        """Filter out files that already have corresponding test files."""
        test_file_bases = set()
        
        # Extract base names from test files
        for test_file in test_files:
            test_path = Path(test_file)
            base_name = test_path.stem
            
            # Remove common test suffixes
            for suffix in ['_test', '_spec', 'Test', 'Spec', 'Tests']:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break
            
            test_file_bases.add(base_name.lower())
        
        # Filter testable files
        files_without_tests = []
        for file_path in testable_files:
            file_base = Path(file_path).stem.lower()
            
            # Check if this file has a corresponding test
            if file_base not in test_file_bases:
                files_without_tests.append(file_path)
        
        return files_without_tests
