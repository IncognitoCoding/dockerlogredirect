"""
This program is designed to redirect docker container logs into a centralized directory.
"""

# Built-in/Generic Imports
import logging
from typing import Union
import traceback
import threading
import subprocess

# Libraries
from functools import partial

# Own module
from ictoolkit.directors.thread_director import start_function_thread
from ictoolkit.directors.validation_director import value_type_validation
from ictoolkit.directors.error_director import error_formatter
from ictoolkit.helpers.py_helper import get_function_name, get_line_number

__author__ = 'IncognitoCoding'
__copyright__ = 'Copyright 2021, log_redirect'
__credits__ = ['IncognitoCoding']
__license__ = 'GPL'
__version__ = '0.13'
__maintainer__ = 'IncognitoCoding'
__status__ = 'Development'


def get_docker_log(container_name: str, container_logger: logging.Logger, exclude: Union[str, list]) -> None:
    """
    Runs a sub-process command to redirect the log output for the docker container.

    Args:
        container_name (str): docker container name
        container_logger (logger): docker container logger used for redirecting log output into a log file
        exclude (str or list): exclude words to remove from the output. Can be in str or list format

    Raises:
        Exception: Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>
        Exception: The sub-process ({processing_args}) failed to run. Raising ValueError to exit the current sub-process thread for container '{container_name}'.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f'=' * 20 + get_function_name() + '=' * 20)
    # Custom flowchart tracking. This is ideal for large projects that move a lot.
    # For any third-party modules, set the flow before making the function call.
    logger_flowchart = logging.getLogger('flowchart')
    logger_flowchart.debug(f'Flowchart --> Function: {get_function_name()}')

    try:
        # Validates required types.
        value_type_validation(container_name, str, __name__, get_line_number())
        value_type_validation(exclude, [str, list], __name__, get_line_number())

        # Requires pre-logger formatting because the logger can not use one line if/else or join without excluding sections of the the output.
        if isinstance(exclude, list):
            formatted_exclude = '  - exclude (list):' + str('\n        - ' + '\n        - '.join(map(str, exclude)))
        else:
            formatted_exclude = f'  - exclude (str):\n        - {exclude}'
        logger.debug(
            'Passing parameters:\n'
            f'  - container_name (str):\n        - {container_name}\n'
            f'  - container_logger (logger):\n        - {container_logger}\n'
            f'{formatted_exclude}\n'
        )

        # Sets processing args that are sent as individual commands.
        # For example: dockeruser@mediadocker1:~$ docker logs transmission
        processing_args = ['docker', 'logs', '-f', container_name]

        logger.debug(f'Starting to redirect the docker container logs for {container_name}')
        logger.debug(f'Setting the processing args that are sent as individual commands.\n  - Processing arguments = {processing_args}')
        logger.debug('If the docker container is not running, it will take a minute to timeout. Please wait...')

        # Runs the subprocess and returns the output from the docker log file and will continue to process new log entries.
        output = subprocess.Popen(processing_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        # Loops through each log entry as the value is received from the subprocess.
        for line in iter(output.stdout.readline, ''):
            # Removes all trailing characters from the log entry.
            line = line.rstrip()
            # Checks if exclude is a str or list.
            if isinstance(exclude, str):
                # Checks that the line does not contain an exclude entry.
                if exclude not in line:
                    # Writes formated output to log file.
                    container_logger.debug(line)
            elif isinstance(exclude, list):
                # Assigns list variable to temporary hold matched excludes determining if the line should write.
                matched_exclude = []
                # Loops through each exclude entry.
                for exclude_entry in exclude:
                    # Checks if the line matches an exclude entry.
                    if exclude_entry in line:
                        # Adds the line to matched_exclude for final verification.
                        # This entry is only used to validate if the list contains an entry.
                        matched_exclude.append(line)
                # Checks that the list is empty, which means no match was found.
                if not matched_exclude:
                    # Writes formated output to log file.
                    container_logger.debug(line)
            elif exclude is None:
                # Writes formated output to log file.
                container_logger.debug(line)
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            raise error
        else:
            error_args = {
                'main_message': f'The sub-process ({processing_args}) failed to run. Raising ValueError to exit the current sub-process thread for container \'{container_name}\'.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)


def create_docker_log_threads(docker_container_loggers: list) -> list:
    """
    Creates individual threads for each docker container. This allows the docker container logs to process in a separate thread. Required to allow the main program to sleep and active to re-check the threads are still running.

    Args:
        docker_container_loggers (list): a list that contains two entries. The first entry is the docker container name, and the second entry is the logger created for the docker container log output.

    Raises:
        Exception: Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>
        Exception: A general exception occurred when attempting to start the function thread.

    Returns:
        list: each docker container log thread status is added as a dictionary into a list. The status key returns 'Started' or 'Failed'
            \\- Example: [[{'Status': 'Started', 'container_name': 'MySoftware1'}], [{'Status': 'Started', 'container_name': 'MySoftware2'}]]
    """
    logger = logging.getLogger(__name__)
    logger.debug(f'=' * 20 + get_function_name() + '=' * 20)

    try:
        # Validates required types.
        value_type_validation(docker_container_loggers, list, __name__, get_line_number())

        # Custom flowchart tracking. This is ideal for large projects that move a lot.
        # For any third-party modules, set the flow before making the function call.
        logger_flowchart = logging.getLogger('flowchart')
        logger_flowchart.debug(f'Flowchart --> Function: {get_function_name()}')
        # Requires pre-logger formatting because the logger can not use one line if/else or join without excluding sections of the the output.
        formatted_docker_container_loggers = '  - docker_container_loggers (list):' + str('\n        - ' + '\n        - '.join(map(str, docker_container_loggers)))
        logger.debug(
            'Passing parameters:\n'
            f'{formatted_docker_container_loggers}\n'
        )

        logger.debug('Creating individual threads for each docker container')
        # Holds tread start information
        thread_start_tracker = []
        # Loops through each docker container being monitored.
        for docker_container in docker_container_loggers:
            # Sets easier to read variables from list.
            # Entry Example: ['MySoftware1', <Logger MySoftware1 (Debug)>, <exclude entry (str or list)>]
            container_name = docker_container[0]
            container_logger = docker_container[1]
            exclude_entries = docker_container[2]
            # Replaces any spaces in the underscores for the thread name
            container_name = container_name.replace(" ", "_")

            # Sets thread name
            thread_name = f'{container_name}_thread'
            thread_start_errors = None
            logger.debug(f'The thread ({thread_name}) is being created for {container_name}')
            # Checks if the start_decryptor_site companion program program is not running for initial startup.
            if thread_name not in str(threading.enumerate()):
                logger.info(f'Starting the docker container log capture for {container_name}')

                # This calls the get_docker_log function and passes the logger details to start monitor the docker container logs.
                # You have to use functools for this to work correctly. Adding the function without functools will cause the function to start before being passed to the start_function_thread.
                start_function_thread(partial(get_docker_log, container_name, container_logger, exclude_entries), thread_name, False)

                # Checks that no errors occurred.
                if thread_start_errors is None:
                    if thread_name in str(threading.enumerate()):
                        # Adds the thread status into tracker dictionary
                        thread_start_tracker.append([{'status': 'started', 'thread_name': thread_name, 'container_name': container_name, 'thread_start_error': None}])
                    else:
                        # Adds the thread status into tracker dictionary
                        thread_start_tracker.append([{'status': 'failed', 'container_name': container_name, 'thread_start_error': None}])
                else:
                    # Adds the thread status into tracker dictionary
                    thread_start_tracker.append([{'status': 'failed', 'thread_name': thread_name, 'container_name': container_name, 'thread_start_errors': thread_start_errors}])
            else:
                # Adds the thread status into tracker dictionary
                thread_start_tracker.append([{'status': 'running', 'thread_name': thread_name, 'container_name': container_name, 'thread_start_error': None}])

        logger.debug(f'Returning value(s):\n  - Return = {thread_start_tracker}')

        return thread_start_tracker
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            raise error
        else:
            error_args = {
                'main_message': 'A general exception occurred when attempting to start the function thread.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)
