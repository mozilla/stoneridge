cd src
./configure --prefix=PATH_TO_STONERIDGE_HOME
make
make install
curl -O http://python-distribute.org/distribute_setup.py
PATH_TO_STONERIDGE_HOME/bin/python distribute_setup.py
PATH_TO_STONERIDGE_HOME/bin/easy_install pip
