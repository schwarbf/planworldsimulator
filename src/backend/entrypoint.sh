#!/bin/sh
# Start as root only to fix the ownership of the data volume (volumes from older images
# belong to root), then run the API as the normal user: it starts agent-written code.
set -e
if [ "$(id -u)" = 0 ]; then
    chown -R app:app /data 2>/dev/null || true
    exec setpriv --reuid=app --regid=app --init-groups "$@"
fi
exec "$@"
