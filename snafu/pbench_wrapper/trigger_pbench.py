import os
import json
import platform
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
        self.redis = args.redis_server
        self.tds = args.tool_data_sink

    def _load_host_info(self):
        pass

    def _check_redis_tds(self):
        if self.create_local:
            return 1

        if not self.redis or not self.tds:
            logger.error("The '--redis-server' and '--tool-data-sink' options are required if '--create-local' is not set to true")
            return 0

        #Add checking for valid hosts(?) - to be experimented with
        return 1

    def _check_local(self, host_tool_dict):
        if not self.create_local:
            return 1

        for host in host_tool_dict.keys():
            if not host == platform.node() and not host == "localhost":
                logger.error(f"Please only use host '{platform.node()}' or 'localhost' with create_local option")
                return 0
        return 1

    def _register_tools(self):
        host_tool_dict = json.load(open(self.tool_dict_path))
        if not self._check_local(host_tool_dict):
            logger.critical("'Create local' mode selected, but remote hosts specified")
            exit(1)
        for host in host_tool_dict.keys():
            args = ["pbench-register-tool", ""]
            if not host == "localhost" and not host == platform.node():
                args.append(f"--remote={host}")
            for tool in host_tool_dict[host]:        
                args[1] = f"--name={tool}"
                subprocess.run(args)   

    def _benchmark_startup(self):
        args = [
            "pbench-tool-meister-start",
            "--sysinfo=default"
        ]
        if self.create_local:
            args.append("--orchestrate=create")
        else:
            args.extend(["--orchestrate=existing", f"--redis-server={self.redis}", f"--tool-data-sink={self.tds}"])
        args.append("default")
        subprocess.run(args)

    def run_benchmark(self):
        if not os.path.exists(self.tool_dict_path):
            logger.critical("Tool mapping file %s not found" % self.tool_dict_path)
            exit(1)

        #Until conditional independence is added:
        if not self._check_redis_tds():
            logger.critical("One or more of --redis-server, --tool-data-sink is missing or invalid")
            exit(1)

        self._register_tools()

        #CREATE NEW BENCHMARK RUN DIR HERE + other setup (if wanted)
        # FIXME - Get these env vars to persist
        os.environ["script"] = "pbench"
        os.environ["config"] = "wrapper-run"
        os.environ["pbench_run_dir"] = "/var/lib/pbench-agent"

        self._benchmark_startup()

        for i in range(1, self.iterations + 1):
            #HANDLE NEW ITERATIONS HERE
            for s in range(1, self.samples + 1):
                #HANDLE NEW SAMPLES HERE
                logger.info(i + s)
        #COLLECT TRANSIENT DATA HERE (SEND RESULTS)

        #INSERT TM STOP CALL HERE
        
        subprocess.run("pbench-clear-tools")