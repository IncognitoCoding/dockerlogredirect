"""
This program is designed to redirect docker container logs into a centralized directory.
"""

# Built-in/Generic Imports
import os
import logging
import pathlib
import time
from datetime import datetime
import re
import yaml

# Own module
from ictoolkit.directors.log_director import setup_logger_yaml
from ictoolkit.directors.yaml_director import read_yaml_config, yaml_value_validation
from ictoolkit.directors.log_director import create_logger
from ictoolkit.directors.email_director import send_email
from ictoolkit.directors.error_director import error_formatter
from ictoolkit.directors.validation_director import value_type_validation
from ictoolkit.helpers.py_helper import get_function_name, get_line_number
from log_redirect.log_redirect import create_docker_log_threads

__author__ = 'IncognitoCoding'
__copyright__ = 'Copyright 2021, DockerLogRedirect'
__credits__ = ['IncognitoCoding']
__license__ = 'GPL'
__version__ = '0.14'
__maintainer__ = 'IncognitoCoding'
__status__ = 'Development'


def create_docker_container_loggers(config_yaml_read: yaml, central_log_path: str) -> list:
    """
    Creates individual docker container loggers for each redirected log docker container. Each logger list will contain the loggers name and any optional exclude entries.

    Rollover enabled on the redirected docker log files. Docker logs on initial startup can contain
    hundreds of lines of output. The rollover will ensure the latest redirect are in the main log file.
    Some duplicate entries may exist between the rolled-over and the new log.

    Args:
        config_yaml_read (yaml): read in YAML configuration
        central_log_path (str): centralized log output directory for all docker container log redirect files

    Raises:
        KeyError: The docker container logger settings are missing required keys.
        Exception: Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>
        Exception: A general error occurred while creating a logger creation for the docker container ({container_name}).
        Exception: Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>
        Exception: A general error occurred while creating docker container loggers.

    Returns:
        list: a list of individual docker container loggers. Each line represents an individual docker container. The line will contain the docker container's name, the docker container logger, and optional exclude entries
            Element Example: ['MySoftware1', '<Logger MySoftware2 (Debug)>', '<Exclude Entries (str or list)>]
    """
    logger = logging.getLogger(__name__)
    logger.debug(f'=' * 20 + get_function_name() + '=' * 20)

    # Checks function launch variables and logs passing parameters.
    try:
        # Validates required types.
        value_type_validation(central_log_path, str, __name__, get_line_number())

        # Custom flowchart tracking. This is ideal for large projects that move a lot.
        # For any third-party modules, set the flow before making the function call.
        logger_flowchart = logging.getLogger('flowchart')
        logger_flowchart.debug(f'Flowchart --> Function: {get_function_name()}')
        logger.debug(
            'Passing parameters:\n'
            f'  - config_yaml_read (yaml):\n        - {config_yaml_read}\n'
            f'  - central_log_path (str):\n        - {central_log_path}\n'
        )
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            raise error
        else:
            error_args = {
                'main_message': 'A general exception occurred during the value type validation.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

    try:
        # Assigns the docker container name and docker container logger to create a multidimensional list.
        # Placement Example: ['MySoftware1', '<Logger MySoftware2 (Debug)>'']
        docker_container_loggers = []
        # Finds all software monitoring entries in the YAML configuration and loops through each one to pull the configuration settings.
        for key, docker_container in config_yaml_read.get('docker_container').items():
            # ####################################################################
            # ###################Dictionary Key Validation########################
            # ####################################################################
            # Gets a list of all expected keys.
            # Return Output: ['container_name', 'log_name', 'max_log_file_size', 'exclude']
            docker_container_keys = list(docker_container.keys())
            # Checks if the key words exist in the dictionary.
            # This validates the correct return dictionary keys from the monitored_software settings.
            if (
                'container_name' not in str(docker_container_keys)
                and 'log_name' not in str(docker_container_keys)
                and 'max_log_file_size' not in str(docker_container_keys)
                and 'exclude' not in str(docker_container_keys)
            ):
                error_args = {
                    'main_message': 'The docker container logger settings are missing required keys.',
                    'error_type': KeyError,
                    'expected_result': ['container_name', 'log_name', 'max_log_file_size', 'exclude'],
                    'returned_result': docker_container_keys,
                    'suggested_resolution': 'Please verify you have set all required keys and try again.',
                }
                error_formatter(error_args, __name__, get_line_number())

            # Gets software configuration settings from the yaml configuration.
            container_name = docker_container.get('container_name')
            log_name = docker_container.get('log_name')
            max_log_file_size = docker_container.get('max_log_file_size')
            exclude = docker_container.get('exclude')

            # Validates the YAML value.
            # Post-processing values are not required because these are optional settings.
            # Optional exclude entries are not validated.
            yaml_value_validation('container_name', container_name, str)
            yaml_value_validation('log_name', log_name, str)
            yaml_value_validation('max_log_file_size', max_log_file_size, int)
            try:
                # Gets/Sets the logger for the docker container.
                #
                # These settings are hardcoded and not user programable in the YAML.
                #
                logger_settings = {
                    'save_path': central_log_path,  # Sets the log save path.
                    'logger_name': container_name,  # Sets the name of the logger.
                    'log_name': log_name,  # Set the name of the log file.
                    'max_bytes': max_log_file_size,  # Sets the max log file size.
                    'file_log_level': 'DEBUG',  # Sets the file log level. Use DEBUG to keep output from going to the console when using the create_logger function with the YAML logger import function (setup_logger_yaml).
                    'console_log_level': 'DEBUG',  # Sets the console log level. Use DEBUG to keep output from going to the console when using the create_logger function with the YAML logger import function (setup_logger_yaml).
                    'backup_count': 4,  # Sets backup copy count
                    'format_option': '%(message)s',  # Sets the log format based on a number option or manual.
                    'handler_option': 2,  # Sets handler option.
                    'rollover': True,  # Sets rollover
                }
                # Calls function to setup logging and create the tracker logger.
                container_logger = create_logger(logger_settings)
                # Takes the docker container name, container logger, and optional exclude entries and creates a single multidimensional list entry.
                docker_container_loggers.append([container_name, container_logger, exclude])
            except Exception as error:
                if 'Originating error on line' in str(error):
                    logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
                    raise error
                else:
                    error_args = {
                        'main_message': f'A general error occurred while creating a logger creation for the docker container ({container_name}).',
                        'error_type': Exception,
                        'original_error': error,
                    }
                    error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

        logger.debug(f'Returning value(s):\n  - Return = {docker_container_loggers}')

        return docker_container_loggers
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            raise error
        else:
            error_args = {
                'main_message': f'A general error occurred while creating docker container loggers.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)


def populate_startup_variables() -> dict:
    """
    This function populates all hard-coded and yaml-configuration variables into a dictionary that is pulled into the main function.
    YAML entry validation checks are performed within this function. No manual configurations are setup within the program. All user
    settings are completed in the "docker_log_redirect.yaml" configuration file.

    Raises:
        KeyError: The 'general' key is missing from the YAML file
        KeyError: The 'software' key is missing from the YAML file
        KeyError: The 'email' key is missing from the YAML file
        Exception: Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>
        Exception: A general error occurred while populating the startup variables.

    Returns:
        dict: A dictionary of all startup variables required for the program to run. These startup variables consist of pre-configured and YAML configuration.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f'=' * 20 + get_function_name() + '=' * 20)
    # Custom flowchart tracking. This is ideal for large projects that move a lot.
    # For any third-party modules, set the flow before making the function call.
    logger_flowchart = logging.getLogger('flowchart')
    logger_flowchart.debug(f'Flowchart --> Function: {get_function_name()}')

    # Initialized an empty dictionary for running variables.
    startup_variables = {}
    # Initialized an empty dictionary for email variables.
    email_settings = {}

    try:
        # Gets the config from the YAML file.
        # Gets the main program root directory.
        main_script_path = pathlib.Path.cwd()
        # Sets the reports directory save path.
        settings_path_name = os.path.abspath(f'{main_script_path}/settings.yaml')
        returned_yaml_read_config = read_yaml_config(settings_path_name, 'FullLoader')

        # Validates required root keys exist in the YAML configuration.
        if 'general' not in returned_yaml_read_config:
            error_args = {
                'main_message': 'The \'general\' key is missing from the YAML file.',
                'error_type': KeyError,
                'suggested_resolution': 'Please verify you have set all required keys and try again.',
            }
            error_formatter(error_args, __name__, get_line_number())
        if 'docker_container' not in returned_yaml_read_config:
            error_args = {
                'main_message': 'The \'docker_container\' key is missing from the YAML file.',
                'error_type': KeyError,
                'suggested_resolution': 'Please verify you have set all required keys and try again.',
            }
            error_formatter(error_args, __name__, get_line_number())
        if 'email' not in returned_yaml_read_config:
            error_args = {
                'main_message': 'The \'email\' key is missing from the YAML file.',
                'error_type': KeyError,
                'suggested_resolution': 'Please verify you have set all required keys and try again.',
            }
            error_formatter(error_args, __name__, get_line_number())

        ##############################################################################
        # Gets the central log path directory.
        #
        central_log_path = returned_yaml_read_config.get('general', {}).get('central_log_path')
        # Validates the YAML value.
        yaml_value_validation('central_log_path', central_log_path, str)
        # Sets the program save path to the script directory.
        central_log_path = os.path.abspath(f'{central_log_path}')
        # Checks if the central_log_path exists and if not it will be created.
        # This is required because the logs do not save to the root directory.
        if not os.path.exists(central_log_path):
            os.makedirs(central_log_path)
        ##############################################################################
        # Gets the option to enable or not enable email alerts.
        email_alerts = returned_yaml_read_config.get('general', {}).get('email_alerts')
        # Validates the YAML value.
        yaml_value_validation('email_alerts', email_alerts, bool)
        # Sets the sleep time in seconds to the startup_variable dictionary
        startup_variables['email_alerts'] = email_alerts
        ##############################################################################
        # Gets the option to enable or not enable program error email alerts.
        #
        alert_program_errors = returned_yaml_read_config.get('general', {}).get('alert_program_errors')
        # Validates the YAML value.
        yaml_value_validation('alert_program_errors', alert_program_errors, bool)
        # Sets the sleep time in seconds to the startup_variable dictionary
        startup_variables['alert_program_errors'] = alert_program_errors
        ##############################################################################
        # Gets/Sets the docker container logger per YAML entry by calling the function using the user-selected docker container name and docker container file name.
        # Each docker container will have its own logger for output.
        #
        # Return Example: [['MySoftware1', <Logger MySoftware1 (Debug)>], ['MySoftware2', <Logger MySoftware2 (Debug)>]]
        docker_container_loggers = create_docker_container_loggers(returned_yaml_read_config, central_log_path)
        # Sets the monitored software settings to the startup_variable dictionary
        startup_variables['docker_container_loggers'] = docker_container_loggers
        ##############################################################################

        # Sets email values.
        smtp = returned_yaml_read_config.get('email', {}).get('smtp')
        authentication_required = returned_yaml_read_config.get('email', {}).get('authentication_required')
        use_tls = returned_yaml_read_config.get('email', {}).get('use_tls')
        username = returned_yaml_read_config.get('email', {}).get('username')
        password = returned_yaml_read_config.get('email', {}).get('password')
        from_email = returned_yaml_read_config.get('email', {}).get('from_email')
        to_email = returned_yaml_read_config.get('email', {}).get('to_email')

        # Manually disabling encryption because sensitive information will not be emailed. Removing the option from YAML.
        send_message_encrypted = False

        # Validates the YAML value.
        yaml_value_validation('smtp', smtp, str)
        yaml_value_validation('authentication_required', authentication_required, bool)
        yaml_value_validation('use_tls', use_tls, bool)
        yaml_value_validation('username', username, str)
        yaml_value_validation('password', password, str)
        yaml_value_validation('from_email', from_email, str)
        yaml_value_validation('to_email', to_email, str)

        # Adds the email_settings into a dictionary.
        email_settings['smtp'] = smtp
        email_settings['authentication_required'] = authentication_required
        email_settings['use_tls'] = use_tls
        email_settings['username'] = username
        email_settings['password'] = password
        email_settings['from_email'] = from_email
        email_settings['to_email'] = to_email
        email_settings['send_message_encrypted'] = send_message_encrypted
        # Sets email dictionary settings to the startup_variable dictionary.
        startup_variables['email_settings'] = email_settings
        ##############################################################################

        # Returns the dictionary with all the startup variables.
        return (startup_variables)
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Forwarding caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            raise error
        else:
            error_args = {
                'main_message': 'A general error occurred while populating the startup variables.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)


def main():
    """
     This function is main program function that controls all the sub-function calls. A loop set to allow this program to run all time and process based on a sleep variable.
    """
    # ############################################################################################
    # ######################Gets the programs main root directory/YAML File Path##################
    # ############################################################################################
    # Gets the main program root directory.
    main_script_path = pathlib.Path.cwd()

    # Checks that the main root program directory has the correct save folders created.
    # Sets the log directory save path.
    save_log_path = os.path.abspath(f'{main_script_path}/logs')
    # Checks if the save_log_path exists and if not it will be created.
    if not os.path.exists(save_log_path):
        os.makedirs(save_log_path)

    # Sets the YAML file configuration location.
    yaml_file_path = os.path.abspath(f'{main_script_path}/settings.yaml')

    try:

        # Calls function to setup the logging configuration with the YAML file.
        setup_logger_yaml(yaml_file_path)
    except Exception as error:
        if 'Originating error on line' in str(error):
            print(error)
            print('Exiting...')
            exit()
        else:
            error_args = {
                'main_message': 'A general error occurred while setting up the logger yaml.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

    logger = logging.getLogger(__name__)
    logger.debug(f'=' * 20 + get_function_name() + '=' * 20)
    # Custom flowchart tracking. This is ideal for large projects that move a lot.
    # For any third-party modules, set the flow before making the function call.
    logger_flowchart = logging.getLogger('flowchart')
    # Deletes the flowchart log if one already exists.
    logger_flowchart.debug(f'Flowchart --> Function: {get_function_name()}')

    logger.info('######################################################################')
    logger.info('                   Docker Log Redirect - New Loop                     ')
    logger.info('######################################################################')

    try:
        # Calls function to pull in the startup variables.
        startup_variables = populate_startup_variables()
    except KeyError as error:
        # KeyError output does not process the escape sequence cleanly. This fixes the output and removes the string double quotes.
        cleaned_error = str(error).replace(r'\n', '\n')[1:-1]
        logger.debug(f'Captured caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
        logger.error(cleaned_error)
        print('Exiting...')
        exit()
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Captured caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            logger.error(error)
            print('Exiting...')
            exit()
        else:
            error_args = {
                'main_message': 'A general error occurred while populating the startup variables.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

    # ####################################################################
    # ###################Dictionary Key Validation########################
    # ####################################################################
    # Gets a list of all expected keys.
    # Return Output: ['email_alerts', 'alert_program_errors', 'email_settings']
    startup_variables_keys = list(startup_variables.keys())
    # Checks if the key words exist in the dictionary.
    # This validates the correct return dictionary keys from the docker log redirect settings.
    if (
        'email_alerts' not in str(startup_variables_keys)
        or 'alert_program_errors' not in str(startup_variables_keys)
        or 'docker_container_loggers' not in str(startup_variables_keys)
        or 'email_settings' not in str(startup_variables_keys)
    ):
        error_args = {
            'main_message': 'The settings.log file is missing required YAML configuration keys.',
            'error_type': KeyError,
            'expected_result': ['email_alerts', 'alert_program_errors', 'docker_container_loggers', 'email_settings'],
            'returned_result': startup_variables_keys,
            'suggested_resolution': 'Please verify you have set all required keys and try again.',
        }
        error_formatter(error_args, __name__, get_line_number())

    # Sets top-level main variables based on the dictionary of presets.
    # Note: Using [] will give KeyError and using get() will return None.
    email_alerts = startup_variables.get('email_alerts')
    alert_program_errors = startup_variables.get('alert_program_errors')
    docker_container_loggers = startup_variables.get('docker_container_loggers')
    email_settings = startup_variables.get('email_settings')

    try:
        # Calls function to monitor the docker logs.
        # Example Return: [[{'Status': 'Started', 'container_name': 'MySoftware1'}], [{'Status': 'Started', 'container_name': 'MySoftware2'}]]
        thread_status = create_docker_log_threads(docker_container_loggers)
        # Sets count on total entries found
        total_thread_status_entries = len(thread_status)
        # Loops through each dictionary in the thread_status list.
        for index, thread_status_of_dictionary in enumerate(thread_status):
            # Loops through each item in the dictionary entry.
            for value in thread_status_of_dictionary:
                # Sets the return dictionary value to a variable.
                status = value.get('status')
                thread_name = value.get('thread_name')
                container_name = value.get('container_name')
                thread_start_errors = value.get('thread_start_errors')
                # Checks the threads status to determine alerts or logger output.
                if 'running' != status:
                    # Checks if email notifications are enabled
                    if email_alerts:
                        logger.info(f'Sending email. Entry {index + 1} of {total_thread_status_entries }')
                        # Calls function to send the email.
                        send_email(email_settings, f'Docker Log Redirect - The event for {container_name} has a status of [{status}]', f'A docker redirect event has occurred. Status of the docker log redirect = {status}')
                    else:
                        logger.info('Email alerting is disabled. The found log event is not be sent')

                    # Checks if the thread had errors while starting.
                    if thread_start_errors is not None:
                        logger.info('Errors occurred while starting one or more threads. Additional details are provided below.')

                        try:
                            # Checks if a thread start errors containing 'timeout has reached' was throw to create a specific email. Timeouts on the thread do not mean the program needs to stop because other threads may run.
                            if 'timeout has reached' in str(thread_start_errors):
                                email_subject_line = 'Docker Log Redirect - Docker Container Not Outputting'
                                # Sets matched info.
                                body = (
                                    f'DockerLogRedirect has detected a container output issue at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.\n'
                                    f'The docker container logs for the thread \"{thread_name}\" have stopped outputting.\n'
                                    'This can happen with the docker container stops running.\n'
                                    'The docker container will be re-checked in 1 hour.'
                                )
                                logger.warning(body)
                            # Checks if the user entered an incorrect program entry.
                            elif 'The system cannot find the file specified' in str(thread_start_errors):
                                # Pulls the subprocess entry name using regex. The .* is used to match any character between ().
                                # Err Example: 2021-04-02 12:33:16|Error|The sub-process (['docker', 'logs', '-f', 'MySoftware1']) failed to run. [WinError 2] The system cannot find the file specified,
                                #              Originating error on line 57 in <__main__>, Error on line 126 in <ictoolkit.directors.thread_director>, Error on line 149 in <__main__> (Module:docker_log_redirect, Function:main,  Line:525)
                                # Result: 'docker', 'logs', '-f', 'MySoftware1'
                                result = re.search(r"\(.*\)", str(thread_start_errors))
                                # Sets the matching result.
                                subprocess_command = result.group(0)
                                email_subject_line = 'Docker Log Redirect - Docker Redirect Command Failed To Run'
                                body = (
                                    f'DockerLogRedirect has detected a docker file location issue at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.\n'
                                    f'The system cannot find the file specified while attempting to run the following sub-process {subprocess_command}.\n'
                                    'Please ensure your host running this program has Docker installed, and the running user has permission to the docker socket.\n'
                                    'The docker container will be re-checked in 1 hour.'
                                )
                                logger.warning(body)
                            # Checks if the user entered a subprocess that didn't get flagged by an incorrect program entry.
                            elif 'The sub-process' in str(thread_start_errors):
                                # Pulls the subprocess entry name using regex. The .* is used to match any character between ().
                                # Err Example: 2021-04-02 12:33:16|Error|The sub-process (['docker', 'logs', '-f', 'MySoftware1']) failed to run, Originating error on line 57 in <__main__>,
                                #              Error on line 126 in <ictoolkit.directors.thread_director>, Error on line 149 in <__main__> (Module:docker_log_redirect, Function:main,  Line:525)
                                # Result: 'docker', 'logs', '-f', 'MySoftware1'
                                result = re.search(r"\(.*\)", str(thread_start_errors))
                                # Sets the matching result.
                                subprocess_command = result.group(0)
                                email_subject_line = 'Docker Log Redirect - Docker Redirect Command Failed To Run'
                                body = (
                                    f'DockerLogRedirect has detected a docker log thread start issue at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.\n'
                                    f'The system countered the following error ({thread_start_errors}) while running the following sub-process {subprocess_command}.\n'
                                    'Please ensure your host running this program has Docker installed, and the running user has permission to the docker socket.\n'
                                    'The docker container will be re-checked in 1 hour.'
                                )
                                logger.warning(body)
                            else:
                                email_subject_line = 'Docker Log Redirect - Program Issue Occurred'
                                body = (
                                    f'DockerLogRedirect has detected a docker log thread start issue at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.\n'
                                    f'Exception Thrown: {thread_start_errors}\n'
                                    'The docker container will be re-checked in 1 hour.'
                                )
                                logger.warning(body)
                        except Exception as error:
                            if 'Originating error on line' in str(error):
                                logger.debug(f'Captured caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
                                logger.error(error)
                                print('Exiting...')
                                exit()
                            else:
                                error_args = {
                                    'main_message': 'A general exception occurred when starting the tracker.',
                                    'error_type': Exception,
                                    'original_error': error,
                                }
                                error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

                        # ##########################################################
                        # Currently the program is exiting on any discovered error.
                        # ##########################################################
                        # Checking if the user chooses not to send program errors to email.
                        if alert_program_errors is True and email_alerts is True:
                            logger.debug('Sending email notification')
                            # Calls function to send the email.
                            send_email(email_settings, email_subject_line, body)
                        else:
                            if alert_program_errors is False:
                                logger.debug(f'The user chooses not to send program errors to email alerts. Outputting error to the log file.')
                            else:
                                logger.debug('The user did not choose an option on sending program errors to email. Outputting error to the log file.')
                elif 'started' == status:
                    logger.info(f'The docker container log capture has started for {container_name}. Thread name = {thread_name}')
                elif 'running' == status:
                    logger.info(f'The thread ({thread_name}) is still running for {container_name}. No action required')
                else:
                    error_args = {
                        'main_message': 'An unknown thread status had returned.',
                        'error_type': ValueError,
                        'expected_result': 'running, started, failed',
                        'returned_result': status,
                    }
                    error_formatter(error_args, __name__, get_line_number())
    except KeyError as error:
        # KeyError output does not process the escape sequence cleanly. This fixes the output and removes the string double quotes.
        cleaned_error = str(error).replace(r'\n', '\n')[1:-1]
        logger.debug(f'Captured caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
        logger.error(cleaned_error)
        print('Exiting...')
        exit()
    except Exception as error:
        if 'Originating error on line' in str(error):
            logger.debug(f'Captured caught {type(error).__name__} at line {error.__traceback__.tb_lineno} in <{__name__}>')
            logger.error(error)
            print('Exiting...')
            exit()
        else:
            error_args = {
                'main_message': 'A general exception occurred when creating the docker log threads.',
                'error_type': Exception,
                'original_error': error,
            }
            error_formatter(error_args, __name__, error.__traceback__.tb_lineno)

    logger.info('The main program will sleep for 1 hour and validate the docker log redirect threads are still running.')


# Checks that this is the main program initiates the classes to start the functions.
if __name__ == "__main__":

    # Prints out at the start of the program.
    print('# ' + '=' * 85)
    print('Author: ' + __author__)
    print('Copyright: ' + __copyright__)
    print('Credits: ' + ', '.join(__credits__))
    print('License: ' + __license__)
    print('Version: ' + __version__)
    print('Maintainer: ' + __maintainer__)
    print('Status: ' + __status__)
    print('# ' + '=' * 85)

    # Loops to keep the main program active.
    # The YAML configuration file will contain a sleep setting within the main function.
    while True:

        try:
            # Calls main function.
            main()

            # 1-hour delay sleep. Each hour the program will check that the threads are still running and the docker container logs are redirecting.
            time.sleep(3600)
        except KeyError as error:
            # KeyError output does not process the escape sequence cleanly. This fixes the output and removes the string double quotes.
            cleaned_error = str(error).replace(r'\n', '\n')[1:-1]
            print(cleaned_error)
            print('Exiting...')
            exit()
        except Exception as error:
            if 'Originating error on line' in str(error):
                print(error)
                print('Exiting...')
                exit()
