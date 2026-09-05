# docker/seccomp

`oreoa-default.json` is the seccomp profile applied to every service
(`security_opt: seccomp:./docker/seccomp/oreoa-default.json` in the
`x-hardened` anchor of `compose.yaml`).

Provenance: pinned copy of the Docker default profile from moby v28.0.4
(`profiles/seccomp/default.json`), owned by this repository from now on.
Any tightening or loosening is a deliberate, journalized change - never an
accidental drift with the Docker daemon version.
