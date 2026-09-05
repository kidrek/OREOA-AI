# OREOA-AI fast-lane worker image (docker_build_spec.md 3.3).
# Step 1 (skeleton): RQ harness + data-layer Python deps only (no forensic
# tools - Dissect/Sigma engines/YARA/ClamAV land at work-order step 2).
ARG BASE_IMAGE

FROM ${BASE_IMAGE}
USER root
COPY requirements-worker-fast.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm -f /tmp/requirements.lock
COPY docker/worker-fast/entrypoint.sh /usr/local/bin/oreoa-worker-entrypoint
RUN chmod 0555 /usr/local/bin/oreoa-worker-entrypoint
# Normalization mappings are data, read-only in the image (S1.6; the parse
# step resolves them via OREOA_MAPPINGS_DIR).
COPY mappings/ /oreoa/mappings/
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.worker", "fast"]
