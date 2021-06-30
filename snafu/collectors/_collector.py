#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base collector class."""
from abc import ABC, abstractmethod
from configparser import ConfigParser
import logging
from snafu import registry
from snafu.config import check_file, ConfigArgument, FuncAction


class Collector(ABC, metaclass=registry.ToolRegistryMeta):
    """
    Abstract Base class for data collectors.

    To use, subclass, set the ``tool_name``, ``args`` and ``metadata`` attributes, and overwrite the
    ``run``, ``cleanup`` and ``setup`` methods.
    """

    tool_name = "_base_collector"
    """
    args: Iterable[ConfigArgument] = tuple()
    metadata: Iterable[str] = ["cluster_name", "user", "uuid"]
    _common_args: Iterable[ConfigArgument] = (
        ConfigArgument(
            "-l",
            "--labels",
            help="Extra labels to add in results exported by benchmark. Format: key1=value1,key2=value2,...",
            dest="labels",
            default=dict(),
            action=LabelParserAction,
        ),
        ConfigArgument("--cluster-name", dest="cluster_name", env_var="clustername", default=None),
        ConfigArgument("--user", dest="user", env_var="test_user", help="Provide user", default=None),
        ConfigArgument(
            "-u", "--uuid", dest="uuid", env_var="uuid", help="Provide UUID for run", default=None
        ),
    )
    """

    def __init__(self, config_file):
        self.logger = logging.getLogger("snafu").getChild(self.tool_name)
        if not check_file(config_file):
            self.logger.critical(
                f"Pbench config file '{config_file}' not found or unreadable"
            )
            exit(1)
        config = ConfigParser()
        config.read(config_file)
        self.set_config_vars(config)

    @abstractmethod
    def set_config_vars(self, config):
        """Retrieve/check all desired data from config file."""

    @abstractmethod
    def startup(self):
        """Perform setup and initialization of persistent data collection processes."""

    @abstractmethod
    def start_sample(self) -> str:
        """Start a data collection sample. Return the sample archive dir."""

    @abstractmethod
    def stop_sample(self):
        """Stop a data collection sample."""

    @abstractmethod
    def shutdown(self):
        """Stop persistent data collection processes and clean up."""
