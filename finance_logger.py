import logging
import os
from sys import platform

formatter = logging.Formatter(f'%(asctime)s - {platform} - %(levelname)s - %(message)s')


logger_dict = {}


def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.addHandler(handler)

    return logger


def setup_log_script(script_name):
    script_name = script_name.split(".")[0]

    logger_dict[script_name] = setup_logger(f"{script_name}.log", f"data/log/{script_name}.log", level=logging.INFO)


def append_log(message, script_name):
    script_name = script_name.split(".")[0]

    if script_name not in logger_dict:
        setup_log_script(script_name)

    logger_dict[script_name].info(message)
    print(message)


def log_time_taken(time_taken, script_name):
    script_name = script_name.split(".")[0]

    time_logger = setup_logger(f"{script_name}_time.log", f"data/log/time/{script_name}_time.log", level=logging.INFO)

    time_logger.info(f"{time_taken:.4f}")

    print(f"Time taken for {script_name}.py: {time_taken:.4f} seconds.")


def was_successful(script_name):
    file_path = f"data/log/{script_name}.log"

    if not os.path.exists(file_path):
        return False

    with open(file_path, "r") as f:
        return f.read().split(" ")[-1].strip() == "success"
