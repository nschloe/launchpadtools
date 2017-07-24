#!/bin/sh -ue

TMP_DIR="/tmp/dockergc-test-launchpadtools/"
rm -rf "$TMP_DIR"
mkdir "$TMP_DIR"

ORIG_DIR="$TMP_DIR/orig"
CACHE="$HOME/.cache/repo/docker-gc"
git -C "$CACHE" pull || git clone "https://github.com/spotify/docker-gc.git" "$CACHE"
git clone --shared "$CACHE" "$ORIG_DIR"
