#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Iterable, List, Tuple, TypedDict
import os
import json
import platform
import re
import subprocess

# TO REMOVE EVENTUALLY
import argparse

from datetime import datetime
from time import sleep
from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.config import ConfigArgument, FuncAction, check_file
from snafu.process import sample_process, ProcessSample

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")

class Uperf(Benchmark):
    """
    Wrapper for the pbench benchmark.
    """

    tool_name = "pbench"
    args = (
        ConfigArgument(
            "-C",
            "--create-local",
            type=str2bool,
            nargs="?",
            const=True,
            default=False,
            help="If true, creates local tm/tds",
        ),
        ConfigArgument(
            "-T",
            "--tool-dict",
            help="Location of json containing host/tool mapping for data collection",
            required=True,
        ),
        ConfigArgument(
            "-s",
            "--samples",
            type=int,
            required=True,
            default=1,
            help="Number of benchmark samples (per iteration)",
        ),
        ConfigArgument(
            "-i",
            "--iterations",
            type=int,
            required=True,
            default=1,
            help="Number of benchmark iterations",
        ),
        ConfigArgument(
            "-l",
            "--sample-length",
            type=int,
            required=True,
            default=20,
            help="Length (time) of collection for each sample",
        ),
        # Make conditionally dependent? (tds and redis)
        ConfigArgument(
            "-R",
            "--redis-server",
            default=None,
            help="Redis 'host:port' or 'host' with default port 17001",
        ),
        ConfigArgument(
            "-D", "--tool-data-sink", default=None, help="Tool-data-sink 'host'",
        )
    )

    def _cleanup_tools(self, message=None):
        if message:
            self.logger.critical(message)
        if self.registered:
            try:
                subprocess.run("pbench-clear-tools")
            except Exception as e:
                self.logger.critical(f"When attempting to clear tools, hit exception: {e}")
                exit(1)

    def _run_process(self, args, env_vars=None):
        try:
            if env_vars:
                subprocess.run(args, env=env_vars)
            else:
                subprocess.run(args)
        except Exception as e:
            self._cleanup_tools(f"Failure to run process: {e}")
            exit(1)

    def _check_redis_tds(self):
        if self.create_local:
            return 1

        if not self.redis or not self.tds:
            self.logger.error(
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
                self.logger.error(
                    f"Please only use host '{platform.node()}' or 'localhost' with create_local option"
                )
                return 0
        return 1

    def _register_tools(self):
        host_tool_dict = json.load(open(self.tool_dict_path))
        if not self._check_local(host_tool_dict):
            self.logger.critical("'Create local' mode selected, but remote hosts specified")
            exit(1)
        for host in host_tool_dict.keys():
            args = ["pbench-register-tool", ""]
            if not host == "localhost" and not host == platform.node():
                args.append(f"--remote={host}")
            for tool in host_tool_dict[host]:
                args[1] = f"--name={tool}"
                self._run_process(args)
        self.registered = True

    def _benchmark_startup(self):
        args = ["pbench-tool-meister-start"] #, "--sysinfo=default"] (CHECK WITH PETER)
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
        self._run_process(args, env_vars=os.environ)

    def _benchmark_shutdown(self):
        args = ["pbench-tool-meister-stop", "--sysinfo=default", "default"]
        self._run_process(args, env_vars=os.environ)

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
        self._run_process(args)

    def setup(self) -> bool:
        """Parse config and check that tool mapping file exists."""
        self.config.parse_args()
        self.logger.debug(f"Got config: {vars(self.config)}")

        if not check_file(self.config.tool_dict_path):
            self.logger.critical(f"Tool mapping file '{self.config.tool_dict_path}' not found or unreadable")
            return False

        return True

    def run(self) -> Iterable[BenchmarkResult]:

        self.logger.info("Running setup tasks.")
        if not self.setup():
            self.logger.critical(f"Something went wrong during setup, refusing to run.")
            exit(1)

        # Until conditional independence is added:
        if not self._check_redis_tds():
            self.logger.critical(
                "One or more of --redis-server, --tool-data-sink is missing or invalid"
            )
            exit(1)

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

        self._benchmark_startup()

        for i in range(1, self.iterations + 1):
            iter_dir = os.environ["benchmark_run_dir"] + f"/iter-{i}"
            self._dir_creator(iter_dir, "iteration dir")
            for s in range(1, self.samples + 1):
                sample_dir = iter_dir + f"/sample-{s}"
                self._dir_creator(sample_dir, "sample dir")
                self.logger.info(
                    f"Beginning {self.sample_length}s sample {s} of iteration {i}"
                )
                self._start_stop_sender("start", sample_dir)
                sleep(self.sample_length)
                self._start_stop_sender("stop", sample_dir)

                # COLLECT TRANSIENT DATA HERE (SEND RESULTS) NOTE: Will def be altered for how we want data
                self.logger.info(f"Sending data for sample {s} of iteration {i}")
                self._start_stop_sender("send", sample_dir)

        self._benchmark_shutdown()

        self._cleanup_tools()
