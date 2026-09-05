# syntax=docker/dockerfile:1.7
# OREOA-AI corpus-ntfs one-shot image (S1.6): debian-slim + ntfs-3g, used by
# `make corpus` to build the raw NTFS images (mkntfs + ntfscp on regular
# files - no mount, no privileged container). Pattern ClamAV (S1.5): the
# host stays clean, the tooling is pinned here.
ARG DEBIAN_IMAGE

FROM ${DEBIAN_IMAGE}
ARG NTFS3G_VERSION
RUN apt-get update \
    && apt-get install -y --no-install-recommends ntfs-3g="${NTFS3G_VERSION}" \
    && rm -rf /var/lib/apt/lists/*
COPY docker/corpus-ntfs/build_ntfs.sh /usr/local/bin/build_ntfs.sh
RUN chmod 0555 /usr/local/bin/build_ntfs.sh
ENTRYPOINT ["/usr/local/bin/build_ntfs.sh"]
