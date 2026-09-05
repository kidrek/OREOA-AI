# syntax=docker/dockerfile:1.7
# OREOA-AI fast-lane worker image (docker_build_spec.md 3.3).
# Step 1: RQ harness + data layer. Step 2 (S2.0): detection engines.
# Engines: hayabusa + chainsaw release binaries and the zircolite source tree
# (pinned tarball - no PyPI package, no binary release), checksum-verified
# against versions.env at build. Rule sets are NEVER baked: they are mounted
# read-only from /knowledge at run time; the image only carries engines.
ARG BASE_IMAGE
ARG DEBIAN_IMAGE

# --- engine fetcher: download + verify the pinned releases -----------------
FROM ${DEBIAN_IMAGE} AS engines
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl unzip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /fetch
# Hayabusa: musl build - the gnu build needs glibc 2.38+, the platform base
# is debian bookworm (glibc 2.36).
ARG HAYABUSA_VERSION
ARG HAYABUSA_SHA256
RUN curl -fsSL -o hayabusa.zip \
      "https://github.com/Yamato-Security/hayabusa/releases/download/v${HAYABUSA_VERSION}/hayabusa-${HAYABUSA_VERSION}-lin-x64-musl.zip" \
    && echo "${HAYABUSA_SHA256}  hayabusa.zip" | sha256sum -c - \
    && mkdir /fetch/hayabusa \
    && unzip -q hayabusa.zip -d /fetch/hayabusa \
    && mv "/fetch/hayabusa/hayabusa-${HAYABUSA_VERSION}-lin-x64-musl" /fetch/hayabusa/hayabusa \
    && rm -rf /fetch/hayabusa/rules hayabusa.zip
ARG CHAINSAW_VERSION
ARG CHAINSAW_SHA256
RUN curl -fsSL -o chainsaw.tar.gz \
      "https://github.com/WithSecureLabs/chainsaw/releases/download/v${CHAINSAW_VERSION}/chainsaw_x86_64-unknown-linux-gnu.tar.gz" \
    && echo "${CHAINSAW_SHA256}  chainsaw.tar.gz" | sha256sum -c - \
    && tar -xzf chainsaw.tar.gz \
    && rm -f chainsaw.tar.gz
ARG ZIRCOLITE_VERSION
ARG ZIRCOLITE_SHA256
RUN curl -fsSL -o zircolite.tar.gz \
      "https://github.com/wagga40/Zircolite/archive/refs/tags/v${ZIRCOLITE_VERSION}.tar.gz" \
    && echo "${ZIRCOLITE_SHA256}  zircolite.tar.gz" | sha256sum -c - \
    && tar -xzf zircolite.tar.gz \
    && mv "Zircolite-${ZIRCOLITE_VERSION}" /fetch/zircolite \
    && rm -f zircolite.tar.gz \
    && cd /fetch/zircolite \
    && rm -rf .forgejo .github tests docs gui pics rules tools \
       pdm.lock pyproject.toml pytest.ini Zircolite.spec Taskfile.yml \
       .dockerignore .gitignore CODE_OF_CONDUCT.md CONTRIBUTING.md \
       README.md SECURITY.md Dockerfile

# --- worker -----------------------------------------------------------------
FROM ${BASE_IMAGE}
USER root
COPY requirements-worker-fast.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm -f /tmp/requirements.lock
# Engines (S2.0): root-owned 0755/0644, never writable by the worker uid.
COPY --from=engines --chown=root:root --chmod=0755 /fetch/hayabusa /oreoa/hayabusa
COPY --from=engines --chown=root:root --chmod=0755 /fetch/chainsaw /oreoa/chainsaw
COPY --from=engines --chown=root:root --chmod=0755 /fetch/zircolite /oreoa/zircolite
COPY docker/worker-fast/zircolite-wrapper.sh /oreoa/bin/zircolite
RUN chmod 0555 /oreoa/bin/zircolite /oreoa/hayabusa/hayabusa /oreoa/chainsaw/chainsaw
COPY docker/worker-fast/entrypoint.sh /usr/local/bin/oreoa-worker-entrypoint
RUN chmod 0555 /usr/local/bin/oreoa-worker-entrypoint
# Normalization mappings are data, read-only in the image (S1.6; the parse
# step resolves them via OREOA_MAPPINGS_DIR).
COPY mappings/ /oreoa/mappings/
ENV PATH="/oreoa/bin:/oreoa/hayabusa:/oreoa/chainsaw:${PATH}" \
    OREOA_ZIRCOLITE_HOME=/oreoa/zircolite
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.worker", "fast"]
