# OREOA-AI fetcher image (docker_build_spec.md 3.6, profile symbol-fetch):
# RQ worker on queue `fetch`, converts Windows PDBs to ISF with pdbconv.
# Egress restricted via the proxy-fetch sidecar (two allow-listed hosts).
ARG BASE_IMAGE

FROM ${BASE_IMAGE}
USER root
COPY requirements-fetcher.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm -f /tmp/requirements.lock
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.fetcher"]
