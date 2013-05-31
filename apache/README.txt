ABOUT
==============================
This is apache 2.2.something, patched to be able to map requests with query
strings to static files on disk. All of the apache code is written by the
usual suspects, the patch for mapping requests with query strings to static
files was written by Nick Hurley <hurley@todesschaf.org>.

INSTALLATION INSTRUCTIONS
==============================
cd src

Edit config.nice, changing the lines with PATH_TO_<whatever> to have the
appropriate paths

./config.nice

make

make install

Edit httpd.conf, changing the lines with PATH_TO_STONERIDGE_HOME to have the
appropriate path, and STONERIDGE_USERNAME to be the appropriate username.

cp httpd.conf PATH_TO_STONERIDGE_HOME/conf/httpd.conf

cp -R htdocs/* PATH_TO_STONERIDGE_HOME/htdocs
