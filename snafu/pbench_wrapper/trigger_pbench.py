import os
import json
import platform
import re
import subprocess
from datetime import datetime
import logging
from time import sleep

logger = logging.getLogger("snafu")


class Trigger_pbench:
    def __init__(self, args):
        self.tool_dict_path = args.tool_dict
        self.iterations = args.iterations
        self.samples = args.samples
        self.create_local = args.create_local
        self.redis = args.redis_server
        self.tds = args.tool_data_sink
        self.sample_length = args.sample_length

    def _cleanup_tools(self, message=None):
        if message:
            logger.critical(message)
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

    def _benchmark_shutdown(self):
        args = ["pbench-tool-meister-stop", "--sysinfo=default", "default"]
        subprocess.run(args, env=os.environ)

    def _dir_creator(self, dir, purpose):
        try:
            os.mkdir(dir)
        except FileExistsError:
            self._cleanup_tools(f"{purpose} '{dir}' already exists")
            exit(1)

    def _start_stop_sender(self, method, dir):
        acceptable = ["start", "stop", "send"]
        if method not in acceptable:
            self._cleanup_tools(
                f"Unkown method '{method}', must be one of: [start, stop, send]"
            )
            exit(1)

        args = [f"pbench-{method}-tools", "--group=default", f"--dir={dir}"]
        subprocess.run(args)

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

        # ADD ERROR CHECKING? (maybe around subprocess calls?)
        self._register_tools()

        # CREATE NEW BENCHMARK RUN DIR HERE + other setup (if wanted)
        os.environ["script"] = "pbench"
        os.environ["config"] = "wrapper-run"
        os.environ["pbench_run"] = "/var/lib/pbench-agent"
        os.environ["pbench_log"] = os.environ["pbench_run"] + "/pbench.log"
        os.environ["_pbench_hostname"] = os.environ[
            "_pbench_full_hostname"
        ] = platform.node()
        os.environ["pbench_install_dir"] = "/opt/pbench-agent"
        os.environ[
            "benchmark_run_dir"
        ] = f"{os.environ['pbench_run']}/{os.environ['script']}_{os.environ['config']}_{datetime.now().strftime('%m-%d-%Y_%H-%M-%S')}"

        self._dir_creator(os.environ["benchmark_run_dir"], "benchmark-run-dir")

        # ADD ERROR CHECKING?
        self._benchmark_startup()

        for i in range(1, self.iterations + 1):
            iter_dir = os.environ["benchmark_run_dir"] + f"/iter-{i}"
            self._dir_creator(iter_dir, "iteration dir")
            for s in range(1, self.samples + 1):
                sample_dir = iter_dir + f"/sample-{s}"
                self._dir_creator(sample_dir, "sample dir")
                logger.info(
                    f"Beginning {self.sample_length}s sample {s} of iteration {i}"
                )
                self._start_stop_sender("start", sample_dir)
                sleep(self.sample_length)
                self._start_stop_sender("stop", sample_dir)

                # COLLECT TRANSIENT DATA HERE (SEND RESULTS) NOTE: Will def be altered for how we want data
                logger.info(f"Sending data for sample {s} of iteration {i}")
                self._start_stop_sender("send", sample_dir)

        # ADD ERROR CHECKING?
        self._benchmark_shutdown()

        self._cleanup_tools()
