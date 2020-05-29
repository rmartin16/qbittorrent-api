#!/bin/bash

set -e

VER=$1
INSTALL_PATH="/opt/qbittorrent"
ORIGDIR="$PWD"

rm -rf ./qBittorrent
git clone https://github.com/qbittorrent/qBittorrent.git
cd qBittorrent

git checkout tags/release-$VER

INSTALL_PATH="/opt/qbittorrent"
./configure --prefix="$INSTALL_PATH" --disable-gui
make clean
make -j$(nproc)
sudo checkinstall --default --nodoc --backup=no --deldesc --pkgname qbittorrent-nox-src --pkgversion $VER
sudo dpkg --purge qbittorrent-nox-src

mv ./qbittorrent-nox-src_* "$ORIGDIR"
cd "$ORIGDIR"
