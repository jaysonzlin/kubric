# Compiles a docker image for blender w/ "import bpy support"
# 
# Compilation happens in two stages:
# 1) Compiles blender from source.
# 2) Installs previously built bpy module along with other dependencies in a fresh image.
# This two stage process reduces the size of the final image because it doesn't include
# the files and dependencies of the build process.

# #################################################################################################
# Stage 1
# #################################################################################################

FROM nvidia/cuda:12.9.0-devel-ubuntu20.04 as build

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

WORKDIR /blenderpy

# --- Install package dependencies
RUN apt-get update --yes --fix-missing && \
    apt-get install --yes --quiet --no-install-recommends \
      python3.9-dev \
      build-essential \
      ca-certificates \
      libopenexr-dev \
      cmake \
      git \
      libffi-dev \
      libssl-dev \
      libx11-dev \
      libxxf86vm-dev \
      libxcursor-dev \
      libxi-dev \
      libxrandr-dev \
      libxinerama-dev \
      libglew-dev \
      subversion

# make python3.9 the default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 10 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 10

# --- Clone and compile Blender

RUN git clone https://github.com/blender/blender.git --branch blender-v2.93-release --depth 1 && \
    cd blender && git submodule update --init --recursive

# To download precompiled SVN libraries locally on the host, run:
# while ! svn checkout https://svn.blender.org/svnroot/bf-blender/tags/blender-2.93-release/lib/linux_centos7_x86_64 docker/lib/linux_centos7_x86_64; do echo "Rate limit or connection error, retrying in 5s..."; sleep 5; done
COPY docker/lib/linux_centos7_x86_64 /blenderpy/lib/linux_centos7_x86_64

# fix an annoying (no-consequence) bpy shutdown error
# see https://github.com/google-research/kubric/issues/65
COPY ./docker/cycles_free_patch.txt /blenderpy/blender
RUN cd blender && patch -p1 < /blenderpy/blender/cycles_free_patch.txt


RUN sed -i 's/(${LLVM_VERSION} VERSION_LESS "4.0.0")/FALSE/g' /blenderpy/blender/build_files/cmake/platform/platform_unix.cmake && \
    sed -i '1i #ifdef __CUDACC__\n#ifndef saturate\n#define saturate(x) __saturatef(x)\n#endif\n#endif' /blenderpy/blender/intern/cycles/util/util_math_float3.h && \
    echo 'set(WITH_CYCLES_OSL OFF CACHE BOOL "" FORCE)' >> /blenderpy/blender/build_files/cmake/config/bpy_module.cmake && \
    echo 'set(WITH_CYCLES_CUDA_BINARIES ON CACHE BOOL "" FORCE)' >> /blenderpy/blender/build_files/cmake/config/bpy_module.cmake && \
    echo 'set(CYCLES_CUDA_BINARIES_ARCH "sm_70;sm_75;sm_80;sm_86;compute_80" CACHE STRING "" FORCE)' >> /blenderpy/blender/build_files/cmake/config/bpy_module.cmake
RUN cd blender && make -j4 bpy

# #################################################################################################
# Stage 2
# #################################################################################################


FROM nvidia/cuda:12.9.0-runtime-ubuntu20.04

LABEL Author="kubric-team <kubric@google.com> Jayson Lin"
LABEL Title="Blender"

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt


# --- Install package dependencies
# TODO: probably do not need all of them, or at least not in their dev version
RUN apt-get update --yes --fix-missing && \
    apt-get install --yes --quiet --no-install-recommends --reinstall \
      python3.9-dev \
      python3.9-distutils \
      build-essential \
      # for GIF creation
      imagemagick \
      # OpenEXR
      libopenexr-dev \
      curl \
      ca-certificates \
      git \
      libffi-dev \
      libssl-dev \
      libx11-dev \
      libxxf86vm-dev \
      libxcursor-dev \
      libxi-dev \
      libxrandr-dev \
      libxinerama-dev \
      libglew-dev \
      zlib1g-dev \
      # further (optional) python build dependencies
      libbz2-dev \
      libgdbm-dev \
      liblzma-dev \
      libncursesw5-dev \
      libreadline-dev \
      libsqlite3-dev \
      #tk-dev \  # installs libpng-dev which leads to blender linking errors
      uuid-dev

# create symlink for RedHat CA bundle compatibility
RUN ln -sf /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-bundle.crt

# make python3.9 the default python and python3
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 10 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 10

# install pip for python 3.9
RUN curl https://bootstrap.pypa.io/pip/3.9/get-pip.py -o get-pip.py && \
    python3.9 get-pip.py && \
    rm get-pip.py

# install bpy module within python3.9 
COPY --from=build /blenderpy/build_linux_bpy/bin/bpy.so /usr/local/lib/python3.9/dist-packages/
COPY --from=build /blenderpy/lib/linux_centos7_x86_64/python/lib/python3.9/site-packages/2.93 /usr/local/lib/python3.9/dist-packages/2.93