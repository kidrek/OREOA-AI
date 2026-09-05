---
description: Add an indicator to the case IOC set
argument-hint: add <value> <type> [source] [confidence]
step: 3
---

Add the IOC $ARGUMENTS to `iocs` through mcp-case (gated, confirmed
only after explicit analyst confirmation). Types: ip, domain, url, md5, sha1,
sha256, email, filename, path, registry_key, mutex, user_agent, account,
other. The value is matched against the evidence on the next ingest step;
matches land in `detections` (engine=ioc). Confirm the addition in French.
