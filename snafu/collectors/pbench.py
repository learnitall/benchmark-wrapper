#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import json
import platform
import argparse
from configparser import ConfigParser
from datetime import datetime
from time import sleep
from snafu.config import check_file
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


class Pbench:
    tool_name = "pbench"

    def __init__(self, config_file):
        self.logger = logging.getLogger("snafu").getChild(self.tool_name)
        if not check_file(config_file):
            self.logger.critical(
                f"Pbench config file '{config_file}' not found or unreadable"
            )
            exit(1)
        config = ConfigParser()
        config.read(config_file)
        self.iterations = config.getint(
            section="BASICS", option="iterations", fallback=1
        )
        self.samples = config.getint(section="BASICS", option="samples", fallback=1)
        self.sample_length = config.getint(
            section="BASICS", option="sample_length", fallback=20
        )
        try:
            self.create_local = str2bool(
                config.get(section="CREATE", option="create_local", fallback="false")
            )
        except Exception as e:
            self.logger.critical(
                f"Invalid create_local option under CREATE section: {e}"
            )
            exit(1)
        self.tool_dict_path = config.get(section="PATHS", option="host_tool_mapping", fallback=None)
        if not self.tool_dict_path:
            self.logger.critical(
                "No host_tool_mapping option specified under PATHS section"
            )
            exit(1)
        if not check_file(self.tool_dict_path):
            self.logger.critical(
                f"Tool mapping file '{self.tool_dict_path}' not found or unreadable"
            )
            exit(1)
        self.redis = config.get(section="CREATE", option="redis", fallback=None)
        self.tds = config.get(section="CREATE", option="tool_data_sink", fallback=None)

    def _cleanup_tools(self, message=None):
        if message:
            self.logger.critical(message)
        if self.registered:
            process: ProcessSample = sample_process("pbench-clear-tools", self.logger)
            if not process.success:
                self.logger.critical(f"When attempting to clear tools, process failed")
                exit(1)
            else:
                logs = process.successful.stderr.split("\n")
                for log in logs[:-1]:
                    self.logger.info(log.strip())

    def _run_process(self, args, env_vars=None):
        if env_vars:
            process: ProcessSample = sample_process(
                args, self.logger, shell=False, env=env_vars
            )
        else:
            process: ProcessSample = sample_process(args, self.logger, shell=False)

        if not process.success:
            self._cleanup_tools(f"Failure to run process: {args[0]}")
            exit(1)
        else:
            if process.successful.stdout:
                self.logger.info(process.successful.stdout.strip())

    def _check_redis_tds(self):
        if self.create_local:
            return 1

        if not self.redis or not self.tds:
            self.logger.error(
                "The 'redis' and 'tool_data_sink' options are required if '--create_local' is not set to true under CREATE"
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
            self.logger.critical(
                "'Create local' mode selected, but remote hosts specified"
            )
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
        args = [
            "pbench-tool-meister-start"
        ]  # , "--sysinfo=default"] (CHECK WITH PETER)
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

    def run(self):
        if not self._check_redis_tds():
            self.logger.critical(
                "One or more of redis-server, tool-data-sink specification is missing or invalid for pbench config"
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
