#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# flake8: noqa
from snafu.collectors._load_collectors import load_collectors
from snafu.collectors._collector import Collector

DETECTED_COLLECTORS = load_collectors()