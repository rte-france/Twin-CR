# 
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
# 

# Docker environment used to build Dynawo, no longer necessary as a binary distribution can be used instead

FROM --platform=linux/amd64 ubuntu:22.04 AS orchestrator_env

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get upgrade -y

# Dynawo package installation.
RUN apt install -y git gcc g++ gfortran autoconf pkgconf automake make libtool cmake hwloc openjdk-8-jdk \
libblas-dev liblpsolve55-dev libarchive-dev doxygen liblapack-dev libexpat1-dev libsqlite3-dev zlib1g-dev \
    gettext patch clang python3-pip libncurses5-dev libreadline-dev libdigest-perl-md5-perl unzip gcovr lcov \
    lsb-release libxml2-utils python3-lxml python3-psutil wget libcurl4-openssl-dev rsync libopenblas-openmp-dev \
    qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools libwebsocketpp-dev bash-completion libzmq3-dev\
    && apt-get clean

RUN apt-get update && apt-get install -y wget tar build-essential; \
    cd /opt; \
    wget https://archives.boost.io/release/1.77.0/source/boost_1_77_0.tar.gz; \
    tar -xvzf boost_1_77_0.tar.gz; \
    cd boost_1_77_0; \
    ./bootstrap.sh --prefix=/usr/local; \
    ./b2 install; \
    cd ..; \
    rm -rf /opt/boost_1_77_0 /opt/boost_1_77_0.tar.gz

RUN apt install -y -q locales

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install ClickHouse-client
RUN apt-get install -y apt-transport-https ca-certificates dirmngr gnupg; \
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754; \
    echo "deb https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list; \
    apt-get update

RUN apt install -y clickhouse-client

# Install ClickHouse-server
RUN apt install -y clickhouse-server

RUN apt install -y libssl-dev

RUN cd /tmp; \
    wget https://github.com/nats-io/nats-server/releases/download/v2.12.2/nats-server-v2.12.2-amd64.deb; \
    dpkg -i nats-server-v2.12.2-amd64.deb

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Utilities
RUN apt install -y gdb valgrind python3-pip python3-dev libxcb* libxkbcommon-x11-0 xserver-xorg xinit mesa-utils libegl1-mesa libegl1-mesa-dev libgbm-dev libgbm1 libgl1-mesa-dev libgl1-mesa-dri libgl1-mesa-glx libglu1-mesa libglu1-mesa-dev

RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:root123' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

EXPOSE 22

# Clean up unnecessary files to reduce image size
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["/usr/sbin/sshd", "-D"]
