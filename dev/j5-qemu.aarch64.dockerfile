FROM arm64v8/ubuntu:18.04

ENV _IS_J5_AARCH64_LINUX true

RUN apt-get update && apt-get upgrade && apt-get -y install --no-install-recommends \
        file \
        vim-gtk \
        curl \
        wget \
        rsync \
        gdb \
        gnupg2 \
        python3 \
        python3-pip \
        python3-setuptools \
        software-properties-common \
    && ln -sf /usr/bin/python3 /usr/bin/python
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
RUN sed -i.bak 's;bionic;focal;g' /etc/apt/sources.list \
    && apt-get update && apt-get -y install --no-install-recommends \
        gcc-9 \
        g++-9 \
        libstdc++-9-dev \
        libc6-dev \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 90 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 90 \
    && mv /etc/apt/sources.list.bak /etc/apt/sources.list \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get -y install --no-install-recommends \
        coinor-libipopt-dev \
        libacl1-dev \
        libasound2-dev \
        libpcap-dev \
        libssl-dev \
        libopenblas-dev \
        libusb-1.0-0-dev \
        libmp3lame-dev \
        libfftw3-dev \
        libudev-dev \
        zlib1g-dev \
        libdouble-conversion-dev \
        libsnappy-dev \
        libglu1-mesa-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
