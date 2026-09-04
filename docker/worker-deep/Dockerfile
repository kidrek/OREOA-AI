# OREOA-AI deep-lane worker image (docker_build_spec.md 3.4).
# Step 1 (skeleton): derives from worker-fast (RQ harness). plaso, Volatility 3,
# capa/FLOSS/DIE and the unified-log parser are added at their work-order steps.
ARG WORKER_FAST_IMAGE

FROM ${WORKER_FAST_IMAGE}
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.worker", "deep"]
