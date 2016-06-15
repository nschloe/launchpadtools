Launchpad tools
===============

[![Build Status](https://travis-ci.org/nschloe/launchpadtools.svg?branch=master)](https://travis-ci.org/nschloe/launchpadtools)
[![Code Health](https://landscape.io/github/nschloe/launchpadtools/master/landscape.svg?style=flat)](https://landscape.io/github/nschloe/launchpadtools/master)
[![PyPi Version](https://img.shields.io/pypi/v/launchpadtools.svg)](https://pypi.python.org/pypi/launchpadtools)
[![PyPi Downloads](https://img.shields.io/pypi/dm/launchpadtools.svg)](https://pypi.python.org/pypi/launchpadtools)


Some tools for easing submission to launchpad.


### Usage

All options are documented under `launchpad-submit -h`.

#### Backporting

Sometimes, new versions of Debian packages are released and not backported to
older Ubuntu releases. Backporting those manually was always a little bit of a
hassle.

With `launchpad-submit`, it becomes easy: Just

  * find the DSC file of the package you want to backport,
  * add a new PPA on launchpad.net, and
  * execute
```
launchpad-submit \
  --dsc "http://http.debian.net/debian/pool/main/m/metis/metis_5.1.0.dfsg-4.dsc" \
  --ubuntu-releases trusty \
  --ppa nschloe/metis-backports
```

#### Submitting from source

Sometimes, you may want to submit a source package with a Debian configuration
that is available somewhere else. This may help setting up a nightly submission
process. As an example, take the nightly submission script for a
[Mixxx PPA](https://launchpad.net/~nschloe/+archive/ubuntu/mixxx-nightly).

```bash
#!/bin/sh -ue

ORIG_DIR=$(mktemp -d)
clone "https://github.com/mixxxdj/mixxx.git" "$ORIG_DIR"

# Extract the version and append the date
VERSION=$(grep "define VERSION" "$ORIG_DIR/src/defs_version.h" | sed "s/[^0-9]*\([0-9][\.0-9]*\).*/\1/")
FULL_VERSION="$VERSION~$(date +"%Y%m%d%H%M%S")"

DEBIAN_DIR=$(mktemp -d)
clone "git://anonscm.debian.org/git/pkg-multimedia/mixxx.git" "$DEBIAN_DIR"

launchpad-submit \
  --orig "$ORIG_DIR" \
  --debian "$DEBIAN_DIR/debian" \
  --ubuntu-releases trusty wily xenial yakkety \
  --ppa nschloe/mixxx-nightly \
  --version-override "$FULL_VERSION" \
  --version-append-hash \
  --update-patches

rm -rf "$ORIG_DIR"
rm -rf "$DEBIAN_DIR"
```

### Distribution
To create a new release

1. bump the `__version__` number,

2. create a Git tag,
    ```
    $ git tag v0.3.1
    $ git push --tags
    ```
    and

3. upload to PyPi:
    ```
    $ make upload
    ```

### License

The launchpadtools are published under the [MIT license](https://en.wikipedia.org/wiki/MIT_License).
