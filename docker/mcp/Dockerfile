# OREOA-AI MCP servers image (docker_build_spec.md 3.5).
# Step 1.4: base + mcp SDK (streamable HTTP :8000) + redis client (mcp-jobs)
# + duckdb (mcp-evidence read-only queries, mcp-case narrow detections.status
# mutation). One image, four entrypoints selected by `command:` in compose.
ARG BASE_IMAGE

FROM ${BASE_IMAGE}
USER root
COPY requirements-mcp.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && rm -f /tmp/requirements.lock
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.mcp_server", "evidence"]
