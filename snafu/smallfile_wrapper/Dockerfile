FROM snafu:latest

RUN dnf install -y --nodocs procps-ng iproute net-tools ethtool nmap iputils && dnf clean all
ADD https://api.github.com/repos/distributed-system-analysis/smallfile/git/refs/heads/master /tmp/bustcache
RUN git clone https://github.com/distributed-system-analysis/smallfile /opt/smallfile --depth 1
RUN ln -sv /opt/smallfile/smallfile_cli.py /usr/local/bin/
RUN ln -sv /opt/smallfile/smallfile_rsptimes_stats.py /usr/local/bin/
