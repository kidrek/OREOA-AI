# OREOA-AI MCP servers image (docker_build_spec.md 3.5): base only.
# Four entrypoints selected by `command:` in compose (streamable HTTP :8000).
ARG BASE_IMAGE

FROM ${BASE_IMAGE}
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "oreoa.mcp_server", "evidence"]
