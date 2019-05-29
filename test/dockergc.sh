#!/bin/sh -ue

TMP_DIR="/tmp/dockergc-test-launchpadtools/"
rm -rf "$TMP_DIR"
mkdir "$TMP_DIR"

CACHE="$HOME/.cache/repo/docker-gc"
git -C "$CACHE" pull || git clone "https://github.com/spotify/docker-gc.git" "$CACHE"
git clone --shared "$CACHE" "$TMP_DIR"
