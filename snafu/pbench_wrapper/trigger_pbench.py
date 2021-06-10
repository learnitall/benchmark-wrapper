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

    def _register_tools(self):
        pass

    def run_benchmark(self):
        if not os.path.exists(self.tool_dict_path):
            logger.critical("Workload file %s not found" % self.workload)
            exit(1)

        self._register_tools() #Add logic to check if remotes are used with create-local (illegal)

        #CREATE BENCHMARK RUN DIR HERE + other setup

        #INSERT TM START CALL HERE (including whether or not to start other things)

        for i in range(1, self.iterations + 1):
            #HANDLE NEW ITERATIONS HERE
            for s in range(1, self.samples + 1):
                #HANDLE NEW SAMPLES HERE
                logger.info(i + s)
        #COLLECT TRANSIENT DATA HERE (SEND RESULTS)

        #INSERT TM STOP CALL HERE
        