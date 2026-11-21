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

fetch freetype-2.15.0.tar.xz \
    https://downloads.sourceforge.net/project/freetype/freetype2/2.15.0/freetype-2.15.0.tar.xz
fetch libpng-1.6.59.tar.xz \
    https://downloads.sourceforge.net/project/libpng/libpng16/1.6.59/libpng-1.6.59.tar.xz
fetch libxml2-2.15.4.tar.xz \
    https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.4.tar.xz
fetch libarchive-3.8.11.tar.xz \
    https://github.com/libarchive/libarchive/releases/download/v3.8.11/libarchive-3.8.11.tar.xz
fetch libvpx-1.17.0.tar.gz \
    https://github.com/webmproject/libvpx/archive/v1.17.0.tar.gz
fetch mpg123-1.33.7.tar.bz2 \
    https://downloads.sourceforge.net/project/mpg123/mpg123/1.33.7/mpg123-1.33.7.tar.bz2
fetch srt-1.5.7.tar.gz \
    https://github.com/Haivision/srt/archive/v1.5.7.tar.gz
