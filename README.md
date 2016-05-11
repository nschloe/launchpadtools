Launchpad tools
===============

[![Code Health](https://landscape.io/github/nschloe/launchpad-tools/master/landscape.svg?style=flat)](https://landscape.io/github/nschloe/launchpad-tools/master)


Some tools for easing submission to launchpad.


Examples
--------

Backporting
-----------

Sometimes, new versions of Debian packages are released and not backported to
older Ubuntu releases. Backporting those manually was always a little bit of a
hassle.

With `launchpad-backport`, it becomes easy: Just

  * find the DSC file of the package you want to backport,
  * add a new PPA on launchpad.net, and
  * execute
```
launchpad-backport
  --orig "http://http.debian.net/debian/pool/main/m/metis/metis_5.1.0.dfsg-4.dsc" \
  --ubuntu-releases trusty \
  --ppa nschloe/metis-backports
```
