import os
import argparse

from .trigger_pbench import Trigger_pbench


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


class pbench_wrapper:
    def __init__(self, parent_parser):
        parser_object = argparse.ArgumentParser(
            description="Pbench Wrapper script",
            parents=[parent_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser = parser_object.add_argument_group("Pbench benchmark")
        parser.add_argument(
            "-C",
            "--create-local",
            type=str2bool,
            nargs="?",
            const=True,
            default=False,
            help="If true, creates local tm/tds",
            required=True,
        )
        parser.add_argument(
            "-T",
            "--tool-dict",
            help="Location of json containing host/tool mapping for data collection",
            required=True,
        )
        parser.add_argument(
            "-s",
            "--samples",
            type=int,
            required=True,
            default=1,
            help="Number of benchmark samples (per iteration)",
        )
        parser.add_argument(
            "-i",
            "--iterations",
            type=int,
            required=True,
            default=1,
            help="Number of benchmark iterations",
        )
        self.args = parser_object.parse_args()

    def run(self):
        pbench_wrapper_obj = Trigger_pbench(self.args)
        yield pbench_wrapper_obj
