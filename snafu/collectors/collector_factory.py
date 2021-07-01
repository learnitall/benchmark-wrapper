from snafu.registry import COLLECTORS

import logging

logger = logging.getLogger("snafu")

def collector_factory(collector_name, config):
    if COLLECTORS.get(collector_name, None) is not None:
        collector = COLLECTORS[collector_name]
        collector_obj = collector(config)
    else:
        collector = None
        collector_obj = None

    if collector is not None:
        logger.info("identified %s as the collector" % collector_name)
        return collector_obj
    else:
        logger.error("Tool name %s is not recognized." % collector_name)
        return 1  # if error return 1 and fail