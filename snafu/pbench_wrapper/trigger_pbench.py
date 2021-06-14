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

    def _cleanup_tools(self):
        subprocess.run("pbench-clear-tools")

    def _check_redis_tds(self):
        if self.create_local:
            return 1

        if not self.redis or not self.tds:
            logger.error(
                "The '--redis-server' and '--tool-data-sink' options are required if '--create-local' is not set to true"
            )
            return 0

        # Add checking for valid hosts(?) - to be experimented with
        return 1

    def _check_local(self, host_tool_dict):
        if not self.create_local:
            return 1

        for host in host_tool_dict.keys():
            if not host == platform.node() and not host == "localhost":
                logger.error(
                    f"Please only use host '{platform.node()}' or 'localhost' with create_local option"
                )
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
        args = ["pbench-tool-meister-start", "--sysinfo=default"]
        if self.create_local:
            os.environ["pbench_tmp"] = os.environ["pbench_run"] + "/tmp"
            args.append("--orchestrate=create")
        else:
            args.extend(
                [
                    "--orchestrate=existing",
                    f"--redis-server={self.redis}",
                    f"--tool-data-sink={self.tds}",
                ]
            )
        args.append("default")
        subprocess.run(args, env=os.environ)

    def run_benchmark(self):
        if not os.path.exists(self.tool_dict_path):
            logger.critical("Tool mapping file %s not found" % self.tool_dict_path)
            exit(1)

        # Until conditional independence is added:
        if not self._check_redis_tds():
            logger.critical(
                "One or more of --redis-server, --tool-data-sink is missing or invalid"
            )
            exit(1)

        self._register_tools()

        # CREATE NEW BENCHMARK RUN DIR HERE + other setup (if wanted)
        os.environ["script"] = "pbench"
        os.environ["config"] = "wrapper-run"
        os.environ["pbench_run"] = "/var/lib/pbench-agent"
        os.environ["pbench_log"]=os.environ["pbench_run"] + "/pbench.log"
        os.environ["_pbench_hostname"] = os.environ[
            "_pbench_full_hostname"
        ] = platform.node()
        os.environ["pbench_install_dir"] = "/opt/pbench-agent"
        os.environ[
            "benchmark_run_dir"
        ] = f"{os.environ['pbench_run']}/{os.environ['script']}_{os.environ['config']}_{datetime.now().strftime('%m-%d-%Y-%H-%M-%S')}"

        try:
            os.mkdir(os.environ["benchmark_run_dir"])
        except FileExistsError:
            logger.critical(
                f"Benchmark-run-dir '{os.environ['benchmark_run_dir']}' already exists"
            )
            self._cleanup_tools()
            exit(1)

        self._benchmark_startup()

        for i in range(1, self.iterations + 1):
            # HANDLE NEW ITERATIONS HERE
            for s in range(1, self.samples + 1):
                # HANDLE NEW SAMPLES HERE
                logger.info(i + s)
        # COLLECT TRANSIENT DATA HERE (SEND RESULTS)

        # INSERT TM STOP CALL HERE

        self._cleanup_tools()
