import os
import shutil
import platform
from pathlib import Path

from abc import ABC, abstractmethod
from cover_agent.lsp_logic.utils.utils import is_forbidden_directory

class BuiltToolAdapterABC(ABC):
    '''
    Abstract base class for built tool specific adapter.
    '''

    @abstractmethod
    def adapt_test_command(self, test_file_relative_path: str) -> str:
        '''
        Adapts the general test command to run a single test file.
        '''
        pass

    @abstractmethod
    def get_coverage_path(self, test_file_relative_path: str) -> Path:
        pass

    @abstractmethod
    def prepare_environment(self):
        '''
        Prepare environment for test running in specific built tool.
        '''
        pass

    @abstractmethod
    def cleanup_environment(self):
        pass

class MavenAdapter(BuiltToolAdapterABC):
    '''
    An adapter to adapt command line argument for maven.
    '''

    def __init__(self, repo_test_command: str, project_root: str):
        self.backup_path = Path('pom.xml.bak')
        self.repo_test_command= repo_test_command
        self.project_root = Path(project_root)
        self.output_directory_variable = "custom.outputDirectory"
        self.default_output_path = Path("target") / Path("vCover")

    def adapt_test_command(self, test_file_relative_path: str) -> str:
        file_name = os.path.basename(test_file_relative_path)
        class_name = os.path.splitext(file_name)[0]
        test_file_relative_path = Path(test_file_relative_path)

        # Remove existing -Dtest arguments
        args = self.repo_test_command.split()
        new_args = []

        for arg in args:
            if arg.startswith('-Dtest=') or arg.startswith('-Djacoco.destFile=') or arg.startswith('-Djacoco.dataFile=') or arg.startswith(f'-D{self.output_directory_variable}'):
                continue
            new_args.append(arg)

        # touch to modify file time so that maven recompiles file
        if platform.system() == "Windows":
            new_args.insert(0, f"(Get-Item {test_file_relative_path.resolve()}).LastWriteTime = Get-Date")
        else:
            new_args.insert(0, f"touch {test_file_relative_path.resolve()}")
        new_args.insert(1, "&&")
            
        new_args.append(f"-Dtest={class_name}")
        new_args.append(f"-Djacoco.destFile={self.default_output_path / Path(f'jacoco-{class_name}.exec')}")
        new_args.append(f"-Djacoco.dataFile={self.default_output_path / Path(f'jacoco-{class_name}.exec')}")
        new_args.append(f"-D{self.output_directory_variable}={self.default_output_path / Path(class_name)}")
        # TODO: maybe split this part out? so adapt_test_command only adapt maven command to run single test?
        return " ".join(new_args)

    def get_coverage_path(self, test_file_relative_path: str):
        file_name = os.path.basename(test_file_relative_path)
        class_name = os.path.splitext(file_name)[0]
        return self.default_output_path / Path(class_name) / Path("jacoco.xml")

    def prepare_environment(self):
        self._edit_pom()

    def _edit_pom(self):
        import xml.etree.ElementTree as ET
    
        # store back up file
        original_file = Path('pom.xml')
        absolute_pom_path = (self.project_root / original_file).resolve()
        absolute_bak_path = (self.project_root / self.backup_path).resolve()
        try:
            shutil.copy2(absolute_pom_path, absolute_bak_path)
        except FileNotFoundError:
            print(f"Error: The file '{original_file}' was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

        tree = ET.parse(absolute_pom_path)
        namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
        outputDirectoryStr = f'{{{namespace["m"]}}}outputDirectory'
        root = tree.getroot()

        jacoco_maven_plugin = root.find("m:build/m:plugins/m:plugin/[m:artifactId='jacoco-maven-plugin']", namespace)
        if jacoco_maven_plugin.find("m:configuration", namespace) == None:
            jacoco_maven_plugin.append(ET.Element(f"{{{namespace['m']}}}configuration"))
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            tree.write(absolute_pom_path)

        configurations = jacoco_maven_plugin.find("m:configuration", namespace)

        config_tags = []
        for config in configurations:
            config_tags.append(config.tag)
            if config.tag == outputDirectoryStr:
                # nah don't bother with alat
                # # if is already a custom text ( has '${}' )
                # if '$' in config.text and '{' in config.text:
                #     self.output_directory_variable = config.text.split('${')[1].split('}')[0]
                # # is a custom hard coded string
                # else:
                config.text = f'${{{self.output_directory_variable}}}'
                ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
                tree.write(absolute_pom_path)

        if outputDirectoryStr not in config_tags:
            new_output_dir_element = ET.Element('outputDirectory')
            new_output_dir_element.text = f'${{{self.output_directory_variable}}}'
            configurations.append(new_output_dir_element)
            # print("no outputDir")
            ET.register_namespace('', 'http://maven.apache.org/POM/4.0.0')
            tree.write(absolute_pom_path)


        # for config in configurations:
        #     print(config.tag)
        #     if config.tag == f'{{{namespace["m"]}}}outputDirectory':
        #         print(config)

    def cleanup_environment(self):
        original_file = Path('pom.xml')
        absolute_pom_path = (self.project_root / original_file).resolve()
        absolute_bak_path = (self.project_root / self.backup_path).resolve()
        shutil.move(absolute_bak_path, absolute_pom_path)
        if self.default_output_path.exists():
            shutil.rmtree(self.default_output_path, ignore_errors=True)

class GradleAdapter(BuiltToolAdapterABC):
    '''
    An adapter to adapt command line argument for gradle.
    '''

    def __init__(self):
        pass

    def adapt_test_command(self, command, test_file):
        return None

    def prepare_environment(self, command: str, project_root: str, unique_id: int):
        pass

    def cleanup_environment(self):
        pass

class PytestAdapter(BuiltToolAdapterABC):
    '''
    An adapter to adapt command line argument for pytest.
    '''

    def __init__(self):
        pass

    def adapt_test_command(self, command, test_file):
        return None

    def prepare_environment(self, command: str, project_root: str, unique_id: int):
        pass

    def cleanup_environment(self):
        pass

# add in support for other built tool here if needed
def get_built_tool_adapter(command: str, project_root: str, language: str) -> BuiltToolAdapterABC:
    for dirpath, dirnames, filenames in os.walk(project_root):
        if not is_forbidden_directory(project_root.__add__(os.sep), language):
            if "pom.xml" in filenames or "mvn" in command:
                return MavenAdapter(command, project_root)
            elif "build.gradle" in filenames or "gradle" in command:
                return GradleAdapter()
            elif "pytest.ini" in filenames or "pytest" in command: 
                return PytestAdapter()
