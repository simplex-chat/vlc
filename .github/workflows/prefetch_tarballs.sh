#!/bin/sh
# Fetch the contrib tarballs that downloads.videolan.org does not mirror.
#
# contrib falls back to the upstream URL for those, with no delay between
# curl's retries, so a brief upstream outage fails the whole build. Fetching
# them up front with a real backoff avoids that; contrib verifies the
# checksums and skips anything already present in tarballs/.
set -eu

fetch() {
    if [ -f "contrib/tarballs/$1" ]; then
        echo "$1: already present"
        return
    fi
    echo "$1: fetching from $2"
    curl -f -L --retry 5 --retry-all-errors --retry-delay 15 \
        --output "contrib/tarballs/$1" -- "$2"
}

mkdir -p contrib/tarballs

fetch libarchive-3.8.0.tar.gz \
    https://github.com/libarchive/libarchive/releases/download/v3.8.0/libarchive-3.8.0.tar.gz
