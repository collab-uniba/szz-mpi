#!/usr/bin/env bash
yum install libgit2 cmake

python3.6 -m venv ./venv
source venv/bin/activate
pip install --upgrade pip

#set MPI path
#export PATH=$PATH:/usr/lib64/openmpi/bin
export PATH=$PATH:$1

# lib2git
export LIBGIT2=$VIRTUAL_ENV
wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz
tar xzf v0.27.0.tar.gz
cd libgit2-0.27.0/
cmake . -DCMAKE_INSTALL_PREFIX=$LIBGIT2
make
make install

#export LDFLAGS="-Wl,-rpath='$LIBGIT2/lib',--enable-new-dtags $LDFLAGS"

cd ../

pip install -r requirements.txt

rm -r -f libgit2-0.27.0
rm -r -f v0.27.0.tar.gz
