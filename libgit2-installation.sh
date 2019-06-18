#!/usr/bin/env bash
cd /usr/local
wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz
tar xzf v0.27.0.tar.gz
cd libgit2-0.27.0/
cmake .
make
make install