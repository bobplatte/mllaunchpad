# -*- coding: utf-8 -*-

"""This module contains functionality for reading and validating the
   configuration.
"""

# Stdlib imports
import logging
import os

# Third-party imports
import yaml  # https://camel.readthedocs.io/en/latest/yamlref.html

# Own project
from mllaunchpad.yaml_loader import Loader

logger = logging.getLogger(__name__)

CONFIG_DEFAULT = "./LAUNCHPAD_CFG.yml"
CONFIG_ENV = os.environ.get("LAUNCHPAD_CFG", CONFIG_DEFAULT)
required_config = {
    # datasources and datasinks are optional
    "model_store": {"location": {}},
    "model": {
        "name": {},
        "version": {},
        "module": {},
        # custom model keys are optional
    },
    # api: is optional because using mllaunchpad's WSGI/Flask API is optional
    # (e.g. when using mllaunchpad's convenience functions in creating Azure functions).
    # You are free to add more custom settings in the config file. For an example, see
    # https://github.com/schuderer/mllaunchpad-template
}


def validate_config(config_dict, required, path=""):
    for item in required:
        path_start = (path + ":") if path else ""
        if item not in config_dict:
            raise ValueError(
                "Missing key in config file: {}".format(path_start + item)
            )
        validate_config(config_dict[item], required[item], path_start + item)


def get_validated_config(filename=CONFIG_ENV):
    """Read the configuration from file and return it as a dict object.

    Validation is not done yet and planned when the configuration is more
    stable.

    Params:
        - filename: path to configuration file
                    (default: environment variable LAUNCHPAD_CFG or
                     file LAUNCHPAD_CFG.yml)

    Returns:
        dict with configuration
    """
    if filename == CONFIG_DEFAULT:
        logger.warning(
            "Config filename environment variable LAUNCHPAD_CFG not set, "
            "using default file: %s",
            repr(CONFIG_DEFAULT),
        )
    logger.info("Loading configuration file %s...", filename)

    with open(filename) as f:
        y = yaml.load(f, Loader)

    validate_config(y, required_config)

    logger.debug("Configuration loaded and validated: %s", y)

    return y
