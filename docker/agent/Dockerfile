# OREOA-AI agent image (docker_build_spec.md 3.2): base + Node LTS + OpenCode.
# Claude Code is installed only under the claude-code profile (not built here).
ARG NODE_IMAGE
ARG BASE_IMAGE

FROM ${NODE_IMAGE} AS node

FROM ${BASE_IMAGE}
USER root
COPY --from=node /usr/local /usr/local
ARG OPENCODE_VERSION
RUN npm install -g --omit=dev "opencode-ai@${OPENCODE_VERSION}" \
    && npm cache clean --force
COPY docker/agent/entrypoint.sh /usr/local/bin/oreoa-agent-entrypoint
RUN chmod 0555 /usr/local/bin/oreoa-agent-entrypoint
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/oreoa-agent-entrypoint"]
CMD ["opencode"]
