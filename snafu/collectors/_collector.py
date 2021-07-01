#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base collector class."""
from abc import ABC, abstractmethod
from configparser import ConfigParser
import logging
from snafu import registry
from snafu.config import check_file


class Collector(ABC, metaclass=registry.CollectorRegistryMeta):
    """
    Abstract Base class for data collectors.

    To use, subclass, set the ``collector_name`` attribute, and overwrite the
    ``set_config_vars``, ``startup``, `start_sample``, `stop_sample``, and 
    ``shutdown`` methods.
    """

    collector_name = "_base_collector"

    def __init__(self, config_file):
        self.logger = logging.getLogger("snafu").getChild(self.collector_name)
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
