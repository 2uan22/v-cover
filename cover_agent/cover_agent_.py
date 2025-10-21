import datetime
import os
import shutil
import sys
import asyncio

from typing import Optional

import wandb

from cover_agent.agent_completion_abc import AgentCompletionABC
from cover_agent.ai_caller import AICaller
from cover_agent.ai_caller_replay import AICallerReplay
from cover_agent.custom_logger import CustomLogger
from cover_agent.default_agent_completion import DefaultAgentCompletion
from cover_agent.record_replay_manager import RecordReplayManager
from cover_agent.settings.config_schema import CoverAgentConfig
from cover_agent.unit_test_db import UnitTestDB
from cover_agent.unit_test_generator import UnitTestGenerator
from cover_agent.unit_test_validator import UnitTestValidator
from cover_agent.build_tool_adapter import *

from cover_agent.lsp_logic.utils.utils_adapt_command import adapt_test_command


class CoverAgent:
    """
    A class that manages the generation and validation of unit tests to achieve desired code coverage.

    This agent coordinates between test generation and validation components, handles file management,
    and tracks the progress of coverage improvements over multiple iterations.
    """

    def __init__(
        self,
        config: CoverAgentConfig,
        task_id: int = None,
        agent_completion: AgentCompletionABC = None,
        built_tool_adapter: Optional[BuiltToolAdapterABC] = None,
        logger: Optional[CustomLogger] = None,
    ):
        """
        Initialize the CoverAgent instance.

        Args:
            config (CoverAgentConfig): Configuration object containing all necessary settings for the agent.
            agent_completion (AgentCompletionABC, optional): Custom agent completion object. Defaults to None,
                in which case a default completion object is initialized.
            built_tool_adapter (BuiltToolAdapterABC, optional): Custom adapter for project's built tool. Defaults to None,
                in which case method calls will fall back to default value
            logger (Optional[CustomLogger], optional): Custom logger instance. Defaults to None,
                in which case a default logger is created.

        Attributes:
            logger (CustomLogger): Logger instance for logging messages.
            config (CoverAgentConfig): Configuration object for the agent.
            agent_completion (AgentCompletionABC): Agent completion object for handling AI interactions.
        """
        self.config = config
        self.generate_log_files = not config.suppress_log_files
        self.adapter = built_tool_adapter
        self.task_id = task_id
        self.total_input_token_count = 0
        self.total_output_token_count = 0

        self.generated_tests_per_iteration = []
        self.accepted_tests_per_iteration = []

        # Initialize logger with file generation flag
        self.logger = logger or CustomLogger.get_logger(__name__, task_id, os.path.basename(config.test_file_path), generate_log_files=self.generate_log_files)
        if config.suppress_log_files:
            self.logger.info("Suppressed all generated log files.")

        self._validate_paths()
        self._duplicate_test_file()

        # Configure the AgentCompletion object
        if agent_completion:
            self.agent_completion = agent_completion
        else:
            self.ai_caller = self._initialize_ai_caller()
            self.agent_completion = DefaultAgentCompletion(
                caller=self.ai_caller, generate_log_files=self.generate_log_files
            )

    async def _setup(self, semaphore: asyncio.Semaphore):
        self.semaphore = semaphore
        # Modify test command for a single test execution if needed
        test_command = self.config.test_command
        new_command_line = None
        test_file_relative_path = os.path.relpath(self.config.test_file_output_path, self.config.project_root)
        if hasattr(self.config, "run_each_test_separately") and self.config.run_each_test_separately:
            # Calculate a relative path for a test file
            # Handle commands from some known frameworks 
            if self.adapter:
                new_command_line = self.adapter.adapt_test_command(test_file_relative_path) 
            else:
                new_command_line = adapt_test_command(test_command, test_file_relative_path)

            if not new_command_line:
                (
                    new_command_line,
                    prompt_tokens,
                    completion_tokens,
                    _,
                ) = await self.agent_completion.adapt_test_command_for_a_single_test_via_ai(
                    # Use AI to adapt test commands
                    test_file_relative_path=test_file_relative_path,
                    test_command=test_command,
                    project_root_dir=self.config.test_command_dir,
                )
                self.total_input_token_count += prompt_tokens
                self.total_output_token_count += completion_tokens

        # Update the test command if successfully modified
        if new_command_line:
            self.config.test_command_original = test_command
            self.config.test_command = new_command_line
            self.logger.info(
                f"Converting test command: `{test_command}`\n to run only a single test: `{new_command_line}`"
            )

        # UnitTestGenerator and UnitTestValidator depends on new_command_line so put here
        # Initialize test generator with configuration
        self.test_gen = UnitTestGenerator(
            source_file_path=self.config.source_file_path,
            test_file_path=self.config.test_file_output_path,
            project_root=self.config.project_root,
            # code_coverage_report_path=self.adapter.get_coverage_path(test_file_relative_path) or self.config.code_coverage_report_path,
            code_coverage_report_path=self.config.code_coverage_report_path,
            test_command=self.config.test_command,
            test_command_dir=self.config.test_command_dir,
            included_files=self.config.included_files,
            all_included_files=self.config.all_included_files,
            coverage_type=self.config.coverage_type,
            additional_instructions=self.config.additional_instructions,
            llm_model=self.config.model,
            use_report_coverage_feature_flag=self.config.use_report_coverage_feature_flag,
            agent_completion=self.agent_completion,
            generate_log_files=self.generate_log_files,
            task_id=self.task_id,
        )

        # Initialize test validator with configuration
        self.test_validator = UnitTestValidator(
            source_file_path=self.config.source_file_path,
            test_file_path=self.config.test_file_output_path,
            project_root=self.config.project_root,
            code_coverage_report_path=self.config.code_coverage_report_path,
            test_command=self.config.test_command,
            test_command_dir=self.config.test_command_dir,
            included_files=self.config.included_files,
            all_included_files=self.config.all_included_files,
            coverage_type=self.config.coverage_type,
            desired_coverage=self.config.desired_coverage,
            additional_instructions=self.config.additional_instructions,
            llm_model=self.config.model,
            use_report_coverage_feature_flag=self.config.use_report_coverage_feature_flag,
            diff_coverage=self.config.diff_coverage,
            comparison_branch=self.config.branch,
            num_attempts=self.config.run_tests_multiple_times,
            agent_completion=self.agent_completion,
            max_run_time_sec=self.config.max_run_time_sec,
            generate_log_files=self.generate_log_files,
            task_id=self.task_id,
            semaphore=self.semaphore,
        )


    @classmethod
    async def create(
        cls,
        config: CoverAgentConfig,
        task_id: int = None,
        agent_completion: AgentCompletionABC = None,
        built_tool_adapter: Optional[BuiltToolAdapterABC] = None,
        semaphore: asyncio.Semaphore = None,
        logger: Optional[CustomLogger] = None,
    ):
        '''
        factory method to hanlde two phase __init__ method and async _setup method
        '''
        cover_agent = cls(config, task_id, agent_completion, built_tool_adapter, logger)
        await cover_agent._setup(semaphore)
        return cover_agent

    def _initialize_ai_caller(self):
        """
        Initialize the appropriate AI caller based on mode and response file availability.

        Returns:
            Union[AICaller, AICallerReplay]: The initialized AI caller instance
        """
        ai_caller_params = {
            "model": self.config.model,
            "api_base": self.config.api_base,
            "max_tokens": 8192,
            "source_file": self.config.source_file_path,
            "test_file": self.config.test_file_path,
            "record_mode": True,
            "generate_log_files": self.generate_log_files,
            "task_id": self.task_id,
        }
        if self.config.record_mode:
            # In record mode, always use AICaller
            self.logger.info("Initializing AICaller in Record mode...")
            return AICaller(**ai_caller_params)
        else:
            # Try to use replay mode if a response file exists
            try:
                replay_manager = RecordReplayManager(record_mode=False, generate_log_files=self.generate_log_files)
                replay_manager.source_file = self.config.source_file_path
                replay_manager.test_file = self.config.test_file_path

                if replay_manager.has_response_file(
                    source_file=self.config.source_file_path, test_file=self.config.test_file_path
                ):
                    self.logger.info("Initializing AICallerReplay (found recorded responses)...")
                    return AICallerReplay(
                        source_file=self.config.source_file_path,
                        test_file=self.config.test_file_path,
                        generate_log_files=self.generate_log_files,
                    )
            except Exception as e:
                self.logger.debug(f"Failed to initialize replay mode: {e}")

            # Fall back to regular AICaller without recording
            self.logger.info("Initializing AICaller without recording (no recorded responses found)")
            ai_caller_params["record_mode"] = False
            return AICaller(**ai_caller_params)

    def _validate_paths(self):
        """
        Validate all required file paths and initialize the test database.

        This method ensures that source files, test files, and project directories exist.
        It also sets up the SQLite database for logging test runs.

        Raises:
            FileNotFoundError: If any required files or directories are missing.
        """
        # Ensure the source file exists
        if not os.path.isfile(self.config.source_file_path):
            raise FileNotFoundError(f"Source file not found at {self.config.source_file_path} for {self.config.test_file_path}")
        # Ensure the test file exists
        if not os.path.isfile(self.config.test_file_path):
            raise FileNotFoundError(f"Test file not found at {self.config.test_file_path}")

        # Ensure the project root exists
        if self.config.project_root and not os.path.isdir(self.config.project_root):
            raise FileNotFoundError(f"Project root not found at {self.config.project_root}")

        # Connect to the test DB

        if self.generate_log_files:
            self.test_db = UnitTestDB(db_connection_string=f"sqlite:///{self.config.log_db_path}")

    def _duplicate_test_file(self):
        """
        Create a copy of the test file at the output location if specified.

        If no output path is provided, uses the original test file path.
        This allows for non-destructive test generation without modifying the original file.
        """
        # If the test file output path is set, copy the test file there
        if self.config.test_file_output_path != "":
            shutil.copy(self.config.test_file_path, self.config.test_file_output_path)
        else:
            # Otherwise, set the test file output path to the current test file
            self.config.test_file_output_path = self.config.test_file_path

    async def init(self):
        """
        Initialize the test generation environment and perform initial analysis.

        Sets up Weights & Biases logging if configured and performs initial test suite analysis
        to establish baseline coverage metrics.

        Returns:
            tuple: Contains failed test runs, language detection results, test framework info,
                  and initial coverage report.
        """
        # Check if user has exported the WANDS_API_KEY environment variable
        if "WANDB_API_KEY" in os.environ:
            # Initialize the Weights & Biases run
            wandb.login(key=os.environ["WANDB_API_KEY"])
            time_and_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            run_name = f"{self.config.model}_" + time_and_date
            wandb.init(project="cover-agent", name=run_name)

        # Run initial test suite analysis
        self.logger.info("Starting initial test suite analysis.")
        await self.test_validator.initial_test_suite_analysis()
        self.logger.info("Initial test suite analysis complete. Getting initial coverage.")
        failed_test_runs, language, test_framework, coverage_report = await self.test_validator.get_coverage()
        self.logger.info("Initial coverage obtained.")

        return failed_test_runs, language, test_framework, coverage_report

    async def generate_and_validate_tests(self, failed_test_runs, language, test_framework, coverage_report):
        """
        Generate new tests and validate their effectiveness.

        Parameters:
            failed_test_runs (list): Previously failed test executions
            language (str): Detected programming language
            test_framework (str): Identified testing framework
            coverage_report (dict): Current coverage metrics
        """
        self.log_coverage()
        self.logger.info("Starting test generation and validation.")
        generated_tests_dict = await self.test_gen.generate_tests(failed_test_runs, language, test_framework, coverage_report)

        num_generated_tests_dict = len(generated_tests_dict.get("new_tests", []))
        self.generated_tests_per_iteration.append(num_generated_tests_dict)

        try:
            test_results = [
                await self.test_validator.validate_test(test) for test in generated_tests_dict.get("new_tests", [])
            ]

            num_accepted = sum(1 for r in test_results if r.get("status") == "PASS")
            self.accepted_tests_per_iteration.append(num_accepted)

            # Insert results into database
            if self.has_test_db():
                for result in test_results:
                    result["prompt"] = self.test_gen.prompt
                    self.test_db.insert_attempt(result)

        except AttributeError as e:
            self.logger.error(f"Failed to validate the tests within {generated_tests_dict}. Error: {e}")

    def has_test_db(self) -> bool:
        """
        Check if the test database is initialized.

        Returns:
            bool: True if the test database is initialized, False otherwise.
        """
        return hasattr(self, "test_db") and self.test_db is not None

    async def check_iteration_progress(self):
        """
        Evaluate current progress towards coverage goals.

        Returns:
            tuple: Contains updated test results, language info, framework details,
                  coverage report, and boolean indicating if target is reached.
        """
        self.logger.info("Starting check iteration progress")
        failed_runs, lang, framework, report = await self.test_validator.get_coverage()
        self.logger.info("Coverage for new iteration obtained.")
        target_reached = self.test_validator.current_coverage >= (self.test_validator.desired_coverage / 100)
        return failed_runs, lang, framework, report, target_reached

    def finalize_test_generation(self, iteration_count) -> (int, int):
        """
        Complete the test generation process and produce final reports.

        Parameters:
            iteration_count (int): Number of iterations performed

        Side effects:
            - Logs final coverage statistics
            - Generates report file
            - Closes Weights & Biases logging if enabled
            - May exit program if strict coverage requirements not met
        """
        current_coverage = round(self.test_validator.current_coverage * 100, 2)
        desired_coverage = self.test_validator.desired_coverage

        if self.test_validator.current_coverage >= (desired_coverage / 100):
            self.logger.info(
                f"Reached above target coverage of {desired_coverage}% "
                f"(Current Coverage: {current_coverage}%) in {iteration_count} iterations."
            )
        elif iteration_count == self.config.max_iterations:
            coverage_type = "diff coverage" if self.config.diff_coverage else "coverage"
            failure_message = (
                f"Reached maximum iteration limit without achieving desired {coverage_type}. "
                f"Current Coverage: {current_coverage}%"
            )

            if self.config.strict_coverage:
                self.logger.error(failure_message)
                sys.exit(2)
            else:
                self.logger.info(failure_message)

        # Log token usage
        total_input_token = (
            self.test_gen.total_input_token_count
            + self.test_validator.total_input_token_count
            + self.total_input_token_count
        )
        total_output_token = (
            self.test_gen.total_output_token_count
            + self.test_validator.total_output_token_count
            + self.total_output_token_count
        )
        self.logger.info(
            f"Total number of input tokens used for LLM model {self.config.model}: "
            f"{total_input_token}"
        )
        self.logger.info(
            f"Total number of output tokens used for LLM model {self.config.model}: "
            f"{total_output_token}"
        )

        # Only generate report if file generation is enabled
        if self.generate_log_files:
            # Generate report and cleanup
            self.test_db.dump_to_report(self.config.report_filepath)
        if "WANDB_API_KEY" in os.environ:
            wandb.finish()

        return total_input_token, total_output_token

    def log_coverage(self):
        """Log current coverage metrics, differentiating between diff coverage and full coverage."""
        if self.config.diff_coverage:
            self.logger.info(f"Current Diff Coverage: {round(self.test_validator.current_coverage * 100, 2)}%")
        else:
            self.logger.info(f"Current Coverage: {round(self.test_validator.current_coverage * 100, 2)}%")
        self.logger.info(f"Desired Coverage: {self.test_validator.desired_coverage}%")

    async def run(self) -> (int, int, list, list, bool):
        """
        Execute the main test generation loop until coverage goals are met or iterations exhausted.

        The process involves:
        1. Initializing the environment
        2. Repeatedly generating and validating tests
        3. Checking progress after each iteration
        4. Finalizing and reporting results

        Returns:
            input token count (int): amount of input token that this CoverAgent uses
            output token count (int): amount of output token that this CoverAgent uses
            target_reached (bool): whether the coverage target was reached
            generated_tests_per_iteration (list[int]): list of amount of tests that were generated per iterations
            accepted_tests_per_iteration (list[int]): list of amount of tests that were accepted per iterations
        """
        iteration_count = 0
        failed_test_runs, language, test_framework, coverage_report = await self.init()

        while iteration_count < self.config.max_iterations:
            self.logger.info(f"Iteration {iteration_count + 1} of {self.config.max_iterations}.")
            await self.generate_and_validate_tests(failed_test_runs, language, test_framework, coverage_report)

            failed_test_runs, language, test_framework, coverage_report, target_reached = (
                await self.check_iteration_progress()
            )
            if target_reached:
                break

            iteration_count += 1

        return (*self.finalize_test_generation(iteration_count), target_reached, self.generated_tests_per_iteration, self.accepted_tests_per_iteration)
