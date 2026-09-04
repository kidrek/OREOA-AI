#!/bin/sh
# Redis entrypoint (docker_build_spec.md 5b): RQ broker only, data on tmpfs.
# ACL: default user disabled, single `rq` user with the password from the
# docker secret, dangerous/scripting command groups denied (final RQ command
# set validated by test at step 1.4).
set -eu

SECRET=/run/secrets/redis_password
if [ ! -r "$SECRET" ]; then
    echo "redis_password secret missing or unreadable" >&2
    exit 1
fi

PW=$(cat "$SECRET")
cat > /tmp/users.acl <<EOF
user default off
user rq on >${PW} ~* &* +@all -@dangerous -@scripting
EOF
chmod 600 /tmp/users.acl

exec redis-server \
    --save "" \
    --appendonly no \
    --maxmemory 256mb \
    --maxmemory-policy noeviction \
    --protected-mode yes \
    --aclfile /tmp/users.acl \
    --dir /data \
    --logfile ""
