# Proxy / proxy-fetch images (docker_build_spec.md 3.6/3.7, deviation journalized
# 2026-09-04): the Alpine tinyproxy package is built without the filter module
# (Filter directive unavailable), so the proxy base is debian:bookworm-slim
# (digest-pinned) with Debian's tinyproxy, which ships filter support.
ARG DEBIAN_IMAGE

FROM ${DEBIAN_IMAGE}
ARG TINYPROXY_VERSION
RUN apt-get update \
    && apt-get install -y --no-install-recommends "tinyproxy=${TINYPROXY_VERSION}" \
    && rm -rf /var/lib/apt/lists/*
COPY tinyproxy.conf.template /etc/tinyproxy/tinyproxy.conf.template
COPY entrypoint.sh /usr/local/bin/oreoa-proxy-entrypoint
RUN chmod 0555 /usr/local/bin/oreoa-proxy-entrypoint
USER 10001:10001
# Runs unprivileged on :8888; the allow-list is rendered at start from
# LLM_ENDPOINTS (FilterDefaultDeny - anything not listed is denied).
ENTRYPOINT ["/usr/local/bin/oreoa-proxy-entrypoint"]
