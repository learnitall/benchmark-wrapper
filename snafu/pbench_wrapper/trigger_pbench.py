import os
import re
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger("snafu")


class Trigger_pbench:
    def __init__(self, args):
        self.tool_dict_path = args.tool_dict
        self.iterations = args.iterations
        self.samples = args.samples
        self.create_local = args.create_local

    def run_benchmark(self):
        if not os.path.exists(self.tool_dict_path):
            logger.critical("Workload file %s not found" % self.workload)
            exit(1)
        for i in range(1, self.iterations + 1):
            for s in range(1, self.samples + 1):
                logger.info(i + s)

        