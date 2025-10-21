import subprocess
import time
import asyncio
import os

from cover_agent.custom_logger import CustomLogger

class Runner:
    @staticmethod
    async def async_run_command(command: str, max_run_time_sec: int = None, semaphore: asyncio.Semaphore = None, cwd: str = None, logger: CustomLogger = None):
        """
        Executes a shell command in a specified working directory and returns its output, error, and exit code.

        Parameters:
            command (str): The shell command to execute.
            max_run_time_sec (int): Maximum allowed runtime in seconds before timeout.
            cwd (str, optional): The working directory in which to execute the command. Defaults to None.

        Returns:
            tuple: A tuple containing the standard output ('stdout'), standard error ('stderr'), exit code ('exit_code'),
                   and the time of the executed command ('command_start_time').
        """
        command_start_time = int(time.time() * 1000)  # Get the current time in milliseconds


        if not semaphore:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                cwd=cwd,
            )
            stdout, stderr = await proc.communicate()
        else:
            if logger:
                logger.info(f"[Semaphore] Task for command starting with '{command}' is WAITING.")
            async with semaphore:
                # max_run_time_sec = max_run_time_sec * 10
                if logger:
                    logger.info(f"[Semaphore] Task for command starting with '{command}' has ACQUIRED permit.")
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True,
                    cwd=cwd,
                )
                # try:
                #     stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=max_run_time_sec)
                # except asyncio.TimeoutError:
                #     proc.kill()
                #     await proc.wait()  # Ensure process is fully terminated
                #     return b"", b"Command timed out", -1, command_start_time
                stdout, stderr = await proc.communicate()
                if logger:
                    logger.info(f"[Semaphore] Task for command starting with '{command}' has FINISHED. Releasing permit.")

        return stdout.decode(errors='ignore'), stderr.decode(errors='ignore'), proc.returncode, command_start_time

    @staticmethod
    def run_command(command: str, max_run_time_sec: int, cwd: str = None):
        """
        Executes a shell command in a specified working directory and returns its output, error, and exit code.

        Parameters:
            command (str): The shell command to execute.
            max_run_time_sec (int): Maximum allowed runtime in seconds before timeout.
            cwd (str, optional): The working directory in which to execute the command. Defaults to None.

        Returns:
            tuple: A tuple containing the standard output ('stdout'), standard error ('stderr'), exit code ('exit_code'),
                   and the time of the executed command ('command_start_time').
        """
        command_start_time = int(time.time() * 1000)  # Get the current time in milliseconds

        try:
           result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=max_run_time_sec,
           )
           return result.stdout, result.stderr, result.returncode, command_start_time
        except subprocess.TimeoutExpired:
            return "", "Command timed out", -1, command_start_time
