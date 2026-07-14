"""
Provides Java specific instantiation of the LanguageServer class. Contains various configurations and settings specific to Java.
"""

import asyncio
import dataclasses
import json
import logging
import os
import pathlib
import shutil
import stat
import sys
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from cover_agent.lsp_logic.multilspy.multilspy_logger import MultilspyLogger
from cover_agent.lsp_logic.multilspy.language_server import LanguageServer
from cover_agent.lsp_logic.multilspy.lsp_protocol_handler.server import (
    ProcessLaunchInfo,
)
from cover_agent.lsp_logic.multilspy.lsp_protocol_handler.lsp_types import (
    InitializeParams,
)
from cover_agent.lsp_logic.multilspy.multilspy_config import MultilspyConfig
from cover_agent.lsp_logic.multilspy.multilspy_settings import MultilspySettings
from cover_agent.lsp_logic.multilspy.multilspy_utils import FileUtils
from cover_agent.lsp_logic.multilspy.multilspy_utils import PlatformUtils
from pathlib import Path, PurePath


@dataclasses.dataclass
class RuntimeDependencyPaths:
    """
    Stores the paths to the runtime dependencies of EclipseJDTLS
    """

    gradle_path: str
    lombok_jar_path: str
    jre_path: str
    jre_home_path: str
    jdtls_launcher_jar_path: str
    jdtls_readonly_config_path: str
    intellicode_jar_path: str
    intellisense_members_path: str


class EclipseJDTLS(LanguageServer):
    """
    The EclipseJDTLS class provides a Java specific implementation of the LanguageServer class
    """

    def __init__(
        self,
        config: MultilspyConfig,
        logger: MultilspyLogger,
        repository_root_path: str,
    ):
        """
        Creates a new EclipseJDTLS instance initializing the language server settings appropriately.
        This class is not meant to be instantiated directly. Use LanguageServer.create() instead.
        """

        runtime_dependency_paths = self.setupRuntimeDependencies(logger, config)
        self.runtime_dependency_paths = runtime_dependency_paths

        # ws_dir is the workspace directory for the EclipseJDTLS server
        ws_dir = str(
            PurePath(
                MultilspySettings.get_language_server_directory(),
                "EclipseJDTLS",
                "workspaces",
                uuid.uuid4().hex,
            )
        )

        # shared_cache_location is the global cache used by Eclipse JDTLS across all workspaces
        shared_cache_location = str(
            PurePath(
                MultilspySettings.get_global_cache_directory(),
                "lsp",
                "EclipseJDTLS",
                "sharedIndex",
            )
        )

        jre_path = self.runtime_dependency_paths.jre_path
        lombok_jar_path = self.runtime_dependency_paths.lombok_jar_path

        jdtls_launcher_jar = self.runtime_dependency_paths.jdtls_launcher_jar_path

        os.makedirs(ws_dir, exist_ok=True)

        data_dir = str(PurePath(ws_dir, "data_dir"))
        jdtls_config_path = str(PurePath(ws_dir, "config_path"))

        jdtls_readonly_config_path = (
            self.runtime_dependency_paths.jdtls_readonly_config_path
        )

        if not os.path.exists(jdtls_config_path):
            shutil.copytree(jdtls_readonly_config_path, jdtls_config_path)

        for static_path in [
            jre_path,
            lombok_jar_path,
            jdtls_launcher_jar,
            jdtls_config_path,
            jdtls_readonly_config_path,
        ]:
            assert os.path.exists(static_path), static_path

        # TODO: Add "self.runtime_dependency_paths.jre_home_path"/bin to $PATH as well
        proc_env = {
            "syntaxserver": "false",
            "JAVA_HOME": self.runtime_dependency_paths.jre_home_path,
        }
        proc_cwd = repository_root_path
        cmd = " ".join(
            [
                jre_path,
                "--add-modules=ALL-SYSTEM",
                "--add-opens",
                "java.base/java.util=ALL-UNNAMED",
                "--add-opens",
                "java.base/java.lang=ALL-UNNAMED",
                "--add-opens",
                "java.base/sun.nio.fs=ALL-UNNAMED",
                "-Declipse.application=org.eclipse.jdt.ls.core.id1",
                "-Dosgi.bundles.defaultStartLevel=4",
                "-Declipse.product=org.eclipse.jdt.ls.core.product",
                "-Djava.import.generatesMetadataFilesAtProjectRoot=false",
                "-Dfile.encoding=utf8",
                "-noverify",
                "-XX:+UseParallelGC",
                "-XX:GCTimeRatio=4",
                "-XX:AdaptiveSizePolicyWeight=90",
                "-Dsun.zip.disableMemoryMapping=true",
                "-Djava.lsp.joinOnCompletion=true",
                "-Xmx3G",
                "-Xms100m",
                "-Xlog:disable",
                "-Dlog.level=ALL",
                f"-javaagent:{lombok_jar_path}",
                f"-Djdt.core.sharedIndexLocation={shared_cache_location}",
                "-jar",
                jdtls_launcher_jar,
                "-configuration",
                jdtls_config_path,
                "-data",
                data_dir,
            ]
        )

        self.service_ready_event = asyncio.Event()
        self.project_ready_event = asyncio.Event()
        self.intellicode_enable_command_available = asyncio.Event()
        self.initialize_searcher_command_available = asyncio.Event()

        super().__init__(
            config,
            logger,
            repository_root_path,
            ProcessLaunchInfo(cmd, proc_env, proc_cwd),
            "java",
        )

    def setupRuntimeDependencies(
        self, logger: MultilspyLogger, config: MultilspyConfig
    ) -> RuntimeDependencyPaths:
        """
        Setup runtime dependencies for EclipseJDTLS.
        """
        platformId = PlatformUtils.get_platform_id()

        if getattr(sys, "frozen", False):
            with open(
                str(
                    Path(sys._MEIPASS)
                    / "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/runtime_dependencies.json"
                ),
                "r",
            ) as f:
                runtimeDependencies = json.load(f)
                del runtimeDependencies["_description"]
            os.makedirs(
                str(
                    PurePath(
                        Path(sys._MEIPASS)
                        / "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/static"
                    )
                ),
                exist_ok=True,
            )
            gradle_path = str(
                PurePath(
                    Path(sys._MEIPASS),
                    "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/static/gradle-7.3.3",
                )
            )
        else:
            with open(
                str(PurePath(os.path.dirname(__file__), "runtime_dependencies.json")),
                "r",
            ) as f:
                runtimeDependencies = json.load(f)
                del runtimeDependencies["_description"]
            os.makedirs(
                str(PurePath(os.path.abspath(os.path.dirname(__file__)), "static")),
                exist_ok=True,
            )
            gradle_path = str(
                PurePath(
                    os.path.abspath(os.path.dirname(__file__)),
                    "static/gradle-7.3.3",
                )
            )

        # assert platformId.value in [
        #     "linux-x64",
        #     "win-x64",
        # ], "Only linux-x64 platform is supported for in multilspy at the moment"

        if not os.path.exists(gradle_path):
            FileUtils.download_and_extract_archive(
                logger,
                runtimeDependencies["gradle"]["platform-agnostic"]["url"],
                str(PurePath(gradle_path).parent),
                runtimeDependencies["gradle"]["platform-agnostic"]["archiveType"],
            )

        assert os.path.exists(gradle_path)

        dependency = runtimeDependencies["vscode-java"][platformId.value]
        if getattr(sys, "frozen", False):
            vscode_java_path = str(
                PurePath(
                    Path(sys._MEIPASS)
                    / "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/static",
                    dependency["relative_extraction_path"],
                )
            )
        else:
            vscode_java_path = str(
                PurePath(
                    os.path.abspath(os.path.dirname(__file__)),
                    "static",
                    dependency["relative_extraction_path"],
                )
            )
        os.makedirs(vscode_java_path, exist_ok=True)
        jre_home_path = str(PurePath(vscode_java_path, dependency["jre_home_path"]))
        jre_path = str(PurePath(vscode_java_path, dependency["jre_path"]))
        lombok_jar_path = str(PurePath(vscode_java_path, dependency["lombok_jar_path"]))
        jdtls_launcher_jar_path = str(
            PurePath(vscode_java_path, dependency["jdtls_launcher_jar_path"])
        )
        jdtls_readonly_config_path = str(
            PurePath(vscode_java_path, dependency["jdtls_readonly_config_path"])
        )
        if not all(
            [
                os.path.exists(vscode_java_path),
                os.path.exists(jre_home_path),
                os.path.exists(jre_path),
                os.path.exists(lombok_jar_path),
                os.path.exists(jdtls_launcher_jar_path),
                os.path.exists(jdtls_readonly_config_path),
            ]
        ):
            FileUtils.download_and_extract_archive(
                logger, dependency["url"], vscode_java_path, dependency["archiveType"]
            )

        # os.chmod(jre_path, stat.S_IEXEC)

        assert os.path.exists(vscode_java_path)
        assert os.path.exists(jre_home_path)
        assert os.path.exists(jre_path)
        assert os.path.exists(lombok_jar_path)
        assert os.path.exists(jdtls_launcher_jar_path)
        assert os.path.exists(jdtls_readonly_config_path)

        dependency = runtimeDependencies["intellicode"]["platform-agnostic"]
        if getattr(sys, "frozen", False):
            intellicode_directory_path = str(
                # PurePath(os.path.abspath(os.path.dirname(sys._MEIPASS)), "static", dependency["relative_extraction_path"])
                PurePath(
                    Path(sys._MEIPASS)
                    / "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/static",
                    dependency["relative_extraction_path"],
                )
            )
        else:
            intellicode_directory_path = str(
                PurePath(
                    os.path.abspath(os.path.dirname(__file__)),
                    "static",
                    dependency["relative_extraction_path"],
                )
            )
        os.makedirs(intellicode_directory_path, exist_ok=True)
        intellicode_jar_path = str(
            PurePath(intellicode_directory_path, dependency["intellicode_jar_path"])
        )
        intellisense_members_path = str(
            PurePath(
                intellicode_directory_path, dependency["intellisense_members_path"]
            )
        )
        if not all(
            [
                os.path.exists(intellicode_directory_path),
                os.path.exists(intellicode_jar_path),
                os.path.exists(intellisense_members_path),
            ]
        ):
            FileUtils.download_and_extract_archive(
                logger,
                dependency["url"],
                intellicode_directory_path,
                dependency["archiveType"],
            )

        assert os.path.exists(intellicode_directory_path)
        assert os.path.exists(intellicode_jar_path)
        assert os.path.exists(intellisense_members_path)

        return RuntimeDependencyPaths(
            gradle_path=gradle_path,
            lombok_jar_path=lombok_jar_path,
            jre_path=jre_path,
            jre_home_path=jre_home_path,
            jdtls_launcher_jar_path=jdtls_launcher_jar_path,
            jdtls_readonly_config_path=jdtls_readonly_config_path,
            intellicode_jar_path=intellicode_jar_path,
            intellisense_members_path=intellisense_members_path,
        )

    def _get_initialize_params(self, repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize parameters for the EclipseJDTLS server.
        """
        # Look into https://github.com/eclipse/eclipse.jdt.ls/blob/master/org.eclipse.jdt.ls.core/src/org/eclipse/jdt/ls/core/internal/preferences/Preferences.java to understand all the options available
        if getattr(sys, "frozen", False):
            with open(
                str(
                    PurePath(
                        Path(sys._MEIPASS)
                        / "cover_agent/lsp_logic/multilspy/language_servers/eclipse_jdtls/initialize_params.json"
                    )
                ),
                "r",
            ) as f:
                d: InitializeParams = json.load(f)
        else:
            with open(
                str(PurePath(os.path.dirname(__file__), "initialize_params.json")), "r"
            ) as f:
                d: InitializeParams = json.load(f)

        del d["_description"]

        if not os.path.isabs(repository_absolute_path):
            repository_absolute_path = os.path.abspath(repository_absolute_path)

        assert d["processId"] == "os.getpid()"
        d["processId"] = os.getpid()

        assert d["rootPath"] == "repository_absolute_path"
        d["rootPath"] = repository_absolute_path

        assert d["rootUri"] == "pathlib.Path(repository_absolute_path).as_uri()"
        d["rootUri"] = pathlib.Path(repository_absolute_path).as_uri()

        assert (
            d["initializationOptions"]["workspaceFolders"]
            == "[pathlib.Path(repository_absolute_path).as_uri()]"
        )
        d["initializationOptions"]["workspaceFolders"] = [
            pathlib.Path(repository_absolute_path).as_uri()
        ]

        assert (
            d["workspaceFolders"]
            == '[\n            {\n                "uri": pathlib.Path(repository_absolute_path).as_uri(),\n                "name": os.path.basename(repository_absolute_path),\n            }\n        ]'
        )
        d["workspaceFolders"] = [
            {
                "uri": pathlib.Path(repository_absolute_path).as_uri(),
                "name": os.path.basename(repository_absolute_path),
            }
        ]

        assert d["initializationOptions"]["bundles"] == ["intellicode-core.jar"]
        bundles = [self.runtime_dependency_paths.intellicode_jar_path]
        d["initializationOptions"]["bundles"] = bundles

        # assert d["initializationOptions"]["settings"]["java"]["configuration"]["runtimes"] == [
        #     {"name": "JavaSE-17", "path": "static/vscode-java/extension/jre/21.0.11-linux-x86_64", "default": True}
        # ]
        d["initializationOptions"]["settings"]["java"]["configuration"]["runtimes"] = [
            {
                "name": "JavaSE-21",
                "path": self.runtime_dependency_paths.jre_home_path,
                "default": True,
            }
        ]

        for runtime in d["initializationOptions"]["settings"]["java"]["configuration"][
            "runtimes"
        ]:
            assert "name" in runtime
            assert "path" in runtime
            assert os.path.exists(runtime["path"]), (
                f"Runtime required for eclipse_jdtls at path {runtime['path']} does not exist"
            )

        assert (
            d["initializationOptions"]["settings"]["java"]["import"]["gradle"]["home"]
            == "abs(static/gradle-7.3.3)"
        )
        d["initializationOptions"]["settings"]["java"]["import"]["gradle"]["home"] = self.runtime_dependency_paths.gradle_path

        d["initializationOptions"]["settings"]["java"]["import"]["gradle"]["java"]["home"] = self.runtime_dependency_paths.jre_path

        d["initializationOptions"]["settings"]["java"]["import"]["maven"]["enabled"] = False
        d["initializationOptions"]["settings"]["java"]["import"]["gradle"]["enabled"] = False
        d["initializationOptions"]["settings"]["java"]["configuration"]["updateBuildConfiguration"] = "disabled"

        return d

    def _ensure_classpath_file(self):
        cp_path = os.path.join(self.repository_root_path, ".classpath")
        if os.path.exists(cp_path):
            import xml.etree.ElementTree as ET

            tree = ET.parse(cp_path)
            root = tree.getroot()
            existing = {
                e.get("path") for e in root.findall(".//classpathentry[@kind='src']")
            }
            if "src/main/java" in existing:
                return
        cp_content = """<?xml version="1.0" encoding="UTF-8"?>
<classpath>
\t<classpathentry kind="con" path="org.eclipse.jdt.launching.JRE_CONTAINER/org.eclipse.jdt.internal.debug.ui.launcher.StandardVMType/JavaSE-21">
\t\t<attributes>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="con" path="org.eclipse.m2e.MAVEN2_CLASSPATH_CONTAINER">
\t\t<attributes>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/classes" path="src/main/java">
\t\t<attributes>
\t\t\t<attribute name="optional" value="true"/>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/test-classes" path="src/test/java">
\t\t<attributes>
\t\t\t<attribute name="optional" value="true"/>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t\t<attribute name="test" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/classes" path="src/main/resources">
\t\t<attributes>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/test-classes" path="src/test/resources">
\t\t<attributes>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t\t<attribute name="test" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/annotation" path="target/generated-sources/annotations">
\t\t<attributes>
\t\t\t<attribute name="optional" value="true"/>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="src" output="target/test-classes" path="target/generated-test-sources/test-annotations">
\t\t<attributes>
\t\t\t<attribute name="optional" value="true"/>
\t\t\t<attribute name="maven.pomderived" value="true"/>
\t\t</attributes>
\t</classpathentry>
\t<classpathentry kind="output" path="target/classes"/>
</classpath>"""
        with open(cp_path, "w") as f:
            f.write(cp_content)
        self.logger.log(f"Wrote .classpath to {cp_path}", logging.INFO)

    @asynccontextmanager
    async def start_server(self) -> AsyncIterator["EclipseJDTLS"]:
        self._ensure_classpath_file()

        async def register_capability_handler(params):
            assert "registrations" in params
            for registration in params["registrations"]:
                if registration["method"] == "textDocument/completion":
                    assert registration["registerOptions"]["resolveProvider"] == True
                    assert registration["registerOptions"]["triggerCharacters"] == [
                        ".",
                        "@",
                        "#",
                        "*",
                        " ",
                    ]
                    self.completions_available.set()
                if registration["method"] == "workspace/executeCommand":
                    if (
                        "java.intellicode.enable"
                        in registration["registerOptions"]["commands"]
                    ):
                        self.intellicode_enable_command_available.set()
            return

        async def lang_status_handler(params):
            # print(f"LSP status: {params}")
            if params["type"] == "ServiceReady" and params["message"] == "ServiceReady":
                self.service_ready_event.set()
            if params["type"] == "ProjectStatus" and params["message"] == "OK":
                self.project_ready_event.set()

        async def execute_client_command_handler(params):
            assert params["command"] == "_java.reloadBundles.command"
            assert params["arguments"] == []
            return []

        async def window_log_message(msg):
            self.logger.log(f"LSP window/logMessage: {msg}", logging.INFO)

        async def do_nothing(params):
            return

        async def show_progress(params):
            self.logger.log(f"- progress: {params}", logging.INFO)

        async def check_experimental_status(params):
            self.logger.log(f"- experimental/serverStatus: {params}", logging.INFO)
            print(f"- experimental/serverStatus: {params}")

        async def publishDiagnostics(params):
            self.logger.log(f"- textDocument/publishDiagnostics: {params}", logging.INFO)

        async def actionableNotification(params):
            self.logger.log(f"- language/actionableNotification: {params}", logging.INFO)

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("language/status", lang_status_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_request(
            "workspace/executeClientCommand", execute_client_command_handler
        )
        self.server.on_notification("$/progress", show_progress)
        self.server.on_notification(
            "textDocument/publishDiagnostics", publishDiagnostics
        )
        self.server.on_notification(
            "language/actionableNotification", actionableNotification
        )
        self.server.on_notification(
            "experimental/serverStatus", check_experimental_status
        )

        async with super().start_server():
            self.logger.log("Starting EclipseJDTLS server process", logging.INFO)
            await self.server.start()
            initialize_params = self._get_initialize_params(self.repository_root_path)

            self.logger.log(
                "Sending initialize request from LSP client to LSP server and awaiting response",
                logging.INFO,
            )
            init_response = await self.server.send.initialize(initialize_params)
            assert init_response["capabilities"]["textDocumentSync"]["change"] == 2
            assert "completionProvider" not in init_response["capabilities"]
            assert "executeCommandProvider" not in init_response["capabilities"]

            self.server.notify.initialized({})

            self.server.notify.workspace_did_change_configuration(
                {"settings": initialize_params["initializationOptions"]["settings"]}
            )

            await self.intellicode_enable_command_available.wait()

            java_intellisense_members_path = (
                self.runtime_dependency_paths.intellisense_members_path
            )
            assert os.path.exists(java_intellisense_members_path)
            intellicode_enable_result = await self.server.send.execute_command(
                {
                    "command": "java.intellicode.enable",
                    "arguments": [True, java_intellisense_members_path],
                }
            )
            assert intellicode_enable_result

            await self.service_ready_event.wait()
            try:
                await asyncio.wait_for(self.project_ready_event.wait(), timeout=60.0)
                self.logger.log("Project indexing completed", logging.INFO)
            except asyncio.TimeoutError:
                self.logger.log(
                    "Project indexing timed out after 60s, proceeding without full index",
                    logging.WARNING,
                )

            yield self

            await self.server.shutdown()
            await self.server.stop()
