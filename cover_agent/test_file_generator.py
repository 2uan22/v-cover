import os
from pathlib import Path
from typing import Tuple, Optional, List


class TestFileGenerator:
    """Generates empty test files with appropriate templates for different languages."""
    
    def __init__(self, project_root: str, language: str):
        self.project_root = Path(project_root)
        self.language = language.lower()
    
    def find_existing_test_file(self, source_file: str, test_files: List[str]) -> Optional[str]:
        """Check if a test file already exists for the given source file."""
        source_path = Path(source_file)
        source_name = source_path.stem
        
        # Common test file naming patterns
        test_patterns = [
            f"test_{source_name}",
            f"{source_name}_test",
            f"{source_name}Test",
            f"{source_name}Tests",
            f"{source_name}Spec",
            source_name  # Sometimes test file has same name in test directory
        ]
        
        for test_file in test_files:
            test_path = Path(test_file)
            test_name = test_path.stem
            
            if test_name in test_patterns:
                # Additional check: verify it's for the same source file
                # This is a simple heuristic - can be enhanced
                return test_file
        
        return None
    
    def get_test_file_path(self, source_file: str) -> str:
        """Generate the appropriate test file path for a source file."""
        source_path = Path(source_file)
        relative_path = source_path.relative_to(self.project_root)
        
        # Determine test directory structure based on language conventions
        if self.language == "python":
            # Python: tests/ or test_ prefix
            test_dir = self.project_root / "tests"
            if not test_dir.exists():
                test_dir = self.project_root / "test"
            
            # Mirror source structure in test directory
            test_file_name = f"test_{source_path.name}"
            test_file_path = test_dir / relative_path.parent / test_file_name
            
        elif self.language == "java":
            # Java: src/test/java mirrors src/main/java
            source_str = str(relative_path)
            if "src/main/java" in source_str:
                test_path = source_str.replace("src/main/java", "src/test/java")
                test_file_name = source_path.stem + "Test.java"
                test_file_path = self.project_root / Path(test_path).parent / test_file_name
            else:
                # Fallback: create test alongside source
                test_file_name = source_path.stem + "Test.java"
                test_file_path = source_path.parent / test_file_name
                
        elif self.language in ["javascript", "typescript"]:
            # JS/TS: __tests__ directory or .test/.spec suffix
            test_dir = source_path.parent / "__tests__"
            if self.language == "javascript":
                test_file_name = f"{source_path.stem}.test.js"
            else:
                test_file_name = f"{source_path.stem}.test.ts"
            test_file_path = test_dir / test_file_name
            
        elif self.language == "csharp":
            # C#: .Tests project or Tests folder
            test_file_name = source_path.stem + "Tests.cs"
            test_dir = source_path.parent / "Tests"
            test_file_path = test_dir / test_file_name
            
        elif self.language == "go":
            # Go: same directory with _test.go suffix
            test_file_name = source_path.stem + "_test.go"
            test_file_path = source_path.parent / test_file_name
            
        elif self.language == "ruby":
            # Ruby: spec/ directory
            test_dir = self.project_root / "spec"
            test_file_name = f"{source_path.stem}_spec.rb"
            test_file_path = test_dir / relative_path.parent / test_file_name
            
        else:
            # Default: test_ prefix in same directory
            test_file_name = f"test_{source_path.name}"
            test_file_path = source_path.parent / test_file_name
        
        return str(test_file_path)
    
    def get_test_template(self, source_file: str) -> str:
        """Generate a basic test template for the given language."""
        source_path = Path(source_file)
        source_name = source_path.stem
        
        # Extract package name for Java
        package_name = ""
        if self.language == "java":
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("package ") and line.endswith(";"):
                            package_name = line[8:-1].strip()  # Remove "package " and ";"
                            break
            except Exception as e:
                print(f"Warning: Could not read package from {source_file}: {e}")
                # If we can't read the file, try to infer from path
                try:
                    relative_path = Path(source_file).relative_to(self.project_root)
                    path_str = str(relative_path)
                    if "src/main/java" in path_str:
                        package_path = path_str.split("src/main/java/")[1]
                        package_name = os.path.dirname(package_path).replace(os.sep, ".")
                    elif "src" in path_str:
                        # Handle other Java project structures
                        src_index = path_str.find("src") + 4
                        package_path = path_str[src_index:]
                        package_name = os.path.dirname(package_path).replace(os.sep, ".")
                    
                    # Clean up package name
                    package_name = package_name.strip(".")
                except:
                    pass
        
        templates = {
            "python": f"""import pytest
import unittest
from unittest.mock import Mock, patch

# Import the module to be tested
# from {source_path.stem} import *


class Test{source_name.title().replace('_', '')}(unittest.TestCase):
    \"\"\"Test cases for {source_name}\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Clean up after tests\"\"\"
        pass
    
    def test_placeholder(self):
        \"\"\"Placeholder test - replace with actual tests\"\"\"
        # TODO: Implement actual test cases
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
""",
            
            "java": f"""{f"package {package_name};" if package_name else "// TODO: Add package declaration"}

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@DisplayName("{source_name} Test")
public class {source_name}Test {{
    
    @BeforeEach
    void setUp() {{
        // Set up test fixtures
    }}
    
    @AfterEach
    void tearDown() {{
        // Clean up after tests
    }}
    
    @Test
    @DisplayName("Placeholder test - replace with actual tests")
    void testPlaceholder() {{
        // TODO: Implement actual test cases
        assertTrue(true);
    }}
}}
""",
            
            "javascript": f"""const {{ describe, it, expect, beforeEach, afterEach }} = require('@jest/globals');

// Import the module to be tested
// const {{ }} = require('./{source_name}');

describe('{source_name}', () => {{
    beforeEach(() => {{
        // Set up test fixtures
    }});
    
    afterEach(() => {{
        // Clean up after tests
    }});
    
    it('should have placeholder test - replace with actual tests', () => {{
        // TODO: Implement actual test cases
        expect(true).toBe(true);
    }});
}});
""",
            
            "typescript": f"""import {{ describe, it, expect, beforeEach, afterEach }} from '@jest/globals';

// Import the module to be tested
// import {{ }} from './{source_name}';

describe('{source_name}', () => {{
    beforeEach(() => {{
        // Set up test fixtures
    }});
    
    afterEach(() => {{
        // Clean up after tests
    }});
    
    it('should have placeholder test - replace with actual tests', () => {{
        // TODO: Implement actual test cases
        expect(true).toBe(true);
    }});
}});
""",
            
            "csharp": f"""using System;
using Xunit;
using Moq;

namespace Tests
{{
    public class {source_name}Tests
    {{
        public {source_name}Tests()
        {{
            // Set up test fixtures
        }}
        
        [Fact]
        public void PlaceholderTest_ReplaceWithActualTests()
        {{
            // TODO: Implement actual test cases
            Assert.True(true);
        }}
    }}
}}
""",
            
            "go": f"""package {source_path.parent.name}

import (
    "testing"
)

func TestPlaceholder(t *testing.T) {{
    // TODO: Implement actual test cases
    if false {{
        t.Errorf("Replace with actual test implementation")
    }}
}}
""",
            
            "ruby": f"""require 'spec_helper'

RSpec.describe '{source_name}' do
  before(:each) do
    # Set up test fixtures
  end
  
  after(:each) do
    # Clean up after tests
  end
  
  describe 'placeholder test' do
    it 'should be replaced with actual tests' do
      # TODO: Implement actual test cases
      expect(true).to be true
    end
  end
end
"""
        }
        
        return templates.get(self.language, f"// TODO: Add test cases for {source_name}")
    
    def generate_test_file(self, source_file: str) -> Tuple[str, str]:
        """Generate test file path and content for a source file."""
        test_file_path = self.get_test_file_path(source_file)
        test_content = self.get_test_template(source_file)
        
        return test_file_path, test_content
