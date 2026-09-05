# syntax=docker/dockerfile:1.7
# OREOA-AI base image (docker_build_spec.md 3.1):
# python 3.12 slim, non-root user oreoa (10001), tini, common system libs.
# No compilers in the final stage; src/oreoa installed as a wheel with the
# pinned requirements.lock. Versions come from versions.env via build args.

ARG PYTHON_IMAGE

FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build
COPY requirements.lock ./
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --no-deps -w /wheels . \
    && pip install --no-cache-dir --prefix=/install --no-deps /wheels/*.whl -r requirements.lock

FROM ${PYTHON_IMAGE}
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tini libmagic1 libewf2 zstd ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
RUN groupadd -g 10001 oreoa \
    && useradd -u 10001 -g 10001 -m -d /home/oreoa -s /usr/sbin/nologin oreoa
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UMASK=027 \
    PYTHONUNBUFFERED=1
USER 10001:10001
WORKDIR /home/oreoa
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-c", "import oreoa; print(oreoa.__version__)"]
