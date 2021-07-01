#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exact copy of snafu/benchmarks/_load_benchmarks.py but for collectors
"""
import sys
import os
import pkgutil
import importlib
import traceback
import logging
from dataclasses import dataclass
from typing import Dict, Tuple, Type, List, Union
from types import TracebackType


_EXC_INFO_TYPE = Union[Tuple[Type[BaseException], BaseException, TracebackType], Tuple[None, None, None]]


@dataclass
class DetectedCollectors:
    imported: List[str]
    failed: List[str]
    errors: Dict[str, _EXC_INFO_TYPE]

    def log(self, logger: logging.Logger, level: int = logging.DEBUG, show_tb: bool = False) -> None:
        logger.log(
            level,
            f"Successfully imported {len(self.imported)} collector modules: {', '.join(self.imported)}",
        )
        logger.log(
            level, f"Failed to import {len(self.failed)} collector modules: {', '.join(self.failed)}",
        )
        if show_tb and len(self.errors) > 0:
            logger.log(level, f"Got the following errors:")
            for collector, exc_info in self.errors.items():
                tb = "".join(traceback.format_exception(*exc_info))
                logger.log(level, f"Collector module {collector} failed to import:\n{tb}")


def load_collectors() -> DetectedCollectors:

    imported, failed, errors = [], [], []
    # __file__ is full path to this module
    module_name = f".{os.path.basename(__file__).replace('.py', '')}"
    # __name__ is module name with full package hierarchy
    package = __name__.replace(module_name, "")
    module_dir = os.path.dirname(__file__)

    for _, module, _ in pkgutil.iter_modules([module_dir]):
        if not module.startswith("_"):
            try:
                # specify relative import using dot notation
                importlib.import_module(f".{module}", package=package)
                imported.append(module)
            except ImportError:
                failed.append(module)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                errors.append(sys.exc_info())

    return DetectedCollectors(imported=imported, failed=failed, errors=dict(zip(failed, errors)))
