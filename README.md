[![Build Status](https://github.com/panda3d/panda3d/workflows/Continuous%20Integration/badge.svg?branch=master)](https://github.com/panda3d/panda3d/actions?query=branch%3Amaster+workflow%3A%22Continuous+Integration%22)
[![OpenCollective](https://opencollective.com/panda3d/backers/badge.svg)](https://opencollective.com/panda3d)
[![OpenCollective](https://opencollective.com/panda3d/sponsors/badge.svg)](https://opencollective.com/panda3d)

Panda3D
=======

<img src="https://avatars2.githubusercontent.com/u/590956?v=3&s=500" align="right" width="200" />

Panda3D is a game engine, a framework for 3D rendering and game development for
Python and C++ programs.  Panda3D is open-source and free for any purpose,
including commercial ventures, thanks to its
[liberal license](https://www.panda3d.org/license/). To learn more about
Panda3D's capabilities, visit the [gallery](https://www.panda3d.org/gallery/)
and the [feature list](https://www.panda3d.org/features/).  To learn how to
use Panda3D, check the [documentation](https://www.panda3d.org/documentation/)
resources. If you get stuck, ask for help from our active
[community](https://discourse.panda3d.org).

Panda3D is licensed under the Modified BSD License.  See the LICENSE file for
more details.

Installing Panda3D
==================

The latest Panda3D SDK can be downloaded from
[this page](https://www.panda3d.org/download/sdk-1-10-15/).
If you are familiar with installing Python packages, you can use
the following command:

```bash
pip install panda3d
```

The easiest way to install the latest development build of Panda3D
into an existing Python installation is using the following command:

```bash
pip install --pre --extra-index-url https://archive.panda3d.org/ panda3d
```

If this command fails, please make sure your version of pip is up-to-date.

If you prefer to install the full SDK with all tools, the latest development
builds can be obtained from [this page](https://www.panda3d.org/download.php?version=devel&sdk).

These are automatically kept up-to-date with the latest GitHub version of Panda.

Building Panda3D
================

Windows
-------

You can build Panda3D with the Microsoft Visual C++ 2017, 2019 or 2022
compiler, which can be downloaded for free from the [Visual Studio site](https://visualstudio.microsoft.com/downloads/).
You will also need to install the [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk),
and if you intend to target Windows Vista, you will also need the
[Windows 8.1 SDK](https://go.microsoft.com/fwlink/p/?LinkId=323507).

You will also need the thirdparty dependency libraries available for
the build scripts to use.  These are available from one of these two URLs,
depending on whether you are on a 32-bit or 64-bit system, or you can
[click here](https://github.com/rdb/panda3d-thirdparty) for instructions on
building them from source.

- https://www.panda3d.org/download/panda3d-1.10.15/panda3d-1.10.15-tools-win64.zip
- https://www.panda3d.org/download/panda3d-1.10.15/panda3d-1.10.15-tools-win32.zip

After acquiring these dependencies, you can build Panda3D from the command
prompt using the following command.  Change the `--msvc-version` option based
on your version of Visual C++; 2022 is 14.3, 2019 is 14.2, 2017 is 14.1, and
2015 is 14.  Remove the `--windows-sdk=10` option if you need to support
Windows Vista, which requires the Windows 8.1 SDK.

```bash
makepanda\makepanda.bat --everything --installer --msvc-version=14.3 --windows-sdk=10 --no-eigen --threads=2
```

When the build succeeds, it will produce an .exe file that you can use to
install Panda3D on your system.

**Note:** you may choose to remove `--no-eigen` and build with Eigen support in
order to improve runtime performance.  However, this will cause the build to
take hours to complete, as Eigen is a heavily template-based library, and the
MSVC compiler does not perform well under those circumstances.

Linux
-----

Building Panda3D on Linux is easy.  All you need is to invoke the makepanda
script using the version of Python that you want Panda3D to be built against.

Run makepanda.py with the --help option to see which options are available.
Usually, you will want to specify the --everything option (which builds with
support for all features for which it detects the prerequisite dependencies)
and the --installer option (which produces an installable .deb or .rpm file
for you to install, depending on your distribution).

The following command illustrates how to build Panda3D with some common
options:
```bash
python3 makepanda/makepanda.py --everything --installer --no-egl --no-gles --no-gles2 --no-opencv
```

You will probably see some warnings saying that it's unable to find several
dependency packages.  You should determine which ones you want to include in
your build and install the respective development packages.  You may visit
[this manual page](https://docs.panda3d.org/1.11/python/distribution/thirdparty-licenses)
for an overview of the various dependencies.

If you are on Ubuntu, this command should cover the most frequently
used third-party packages:

```bash
sudo apt-get install build-essential pkg-config fakeroot python3-dev libpng-dev libjpeg-dev libtiff-dev zlib1g-dev libssl-dev libx11-dev libgl1-mesa-dev libxrandr-dev libxxf86dga-dev libxcursor-dev bison flex libfreetype6-dev libvorbis-dev libeigen3-dev libopenal-dev libode-dev libbullet-dev nvidia-cg-toolkit libgtk-3-dev libassimp-dev libopenexr-dev
```

Once Panda3D has built, you can either install the .deb or .rpm package that
is produced, depending on which Linux distribution you are using.  For example,
to install the package on Debian or Ubuntu, use this:

```bash
sudo dpkg -i panda3d*.deb
```

If you are not using a Linux distribution that supports .deb or .rpm packages, you
may have to use the installpanda.py script instead, which will directly copy the
files into the appropriate locations on your computer.  You may have to run the
`ldconfig` tool in order to update your library cache after installing Panda3D.

Alternatively, you can add the `--wheel` option, which will produce a .whl
file that can be installed into a Python installation using `pip`.

macOS
-----

On macOS, you will need to download a set of precompiled thirdparty packages in order to
compile Panda3D, which can be acquired from [here](https://www.panda3d.org/download/panda3d-1.10.15/panda3d-1.10.15-tools-mac.tar.gz).

After placing the thirdparty directory inside the panda3d source directory,
you may build Panda3D using a command like the following:

```bash
python makepanda/makepanda.py --everything --installer
```

You may target a specific minimum macOS version using the --osxtarget flag
followed by the release number, eg. 10.9 or 10.14.

If the build was successful, makepanda will have generated a .dmg file in
the source directory containing the installer.  Simply open it and run the
package file in order to install the SDK onto your system.

FreeBSD
-------

Building on FreeBSD is very similar to building on Linux.  You will need to
install the requisite packages using the system package manager.  To install
the recommended set of dependencies, you can use this command:

```bash
pkg install pkgconf bison png jpeg-turbo tiff freetype2 harfbuzz eigen squish openal opusfile libvorbis libX11 mesa-libs ode bullet assimp openexr
```

You will also need to choose which version of Python you want to use.
Install the appropriate package for it (such as `python37` or `python38`) and
run the makepanda script with your chosen Python version:

```bash
python3.11 makepanda/makepanda.py --everything --installer --no-egl --no-gles --no-gles2
```

If successful, this will produce a .pkg file in the root of the source
directory which you can install using `pkg install`.

Android
-------

Although it's possible to build Panda3D on an Android device using the
[termux](https://termux.com/) shell, the recommended route is to cross-compile
.whl files using the SDK and NDK, which can then be used by the `build_apps`
command to build a Python application into an .apk or .aab bundle.  You will
need to get the latest thirdparty packages, which can be obtained from here:

https://rdb.name/thirdparty-android.tar.gz

This includes a copy of Python 3.13 compiled for Android.  You will need to
use Python 3.13 on the host as well.

These commands show how to compile wheels for the supported Android ABIs:

```bash
export ANDROID_SDK_ROOT=/home/rdb/local/android
python3.13 makepanda/makepanda.py --everything --outputdir built-droid-arm64 --arch arm64 --target android-21 --threads 6 --wheel
python3.13 makepanda/makepanda.py --everything --outputdir built-droid-armv7a --arch arm --target android-21 --threads 6 --wheel
python3.13 makepanda/makepanda.py --everything --outputdir built-droid-x86_64 --arch x86_64 --target android-21 --threads 6 --wheel
python3.13 makepanda/makepanda.py --everything --outputdir built-droid-x86 --arch x86 --target android-21 --threads 6 --wheel
```

It is now possible to use the generated wheels with `build_apps`, as explained
on this page:

https://discourse.panda3d.org/t/deployment-for-android/28226

Running Tests
=============

Install [PyTest](https://docs.pytest.org/en/latest/getting-started.html#installation)
and run the `pytest` command.  If you have not installed Panda3D, you will
need to configure your environment by pointing the `PYTHONPATH` variable at
the `built` directory.  On Linux, you will also need to point the
`LD_LIBRARY_PATH` variable at the `built/lib` directory.

As a convenience, you can alternatively pass the `--tests` option to makepanda.

Reporting Issues
================

If you encounter any bugs when using Panda3D, please report them in the bug
tracker.  This is hosted at:

  https://github.com/panda3d/panda3d/issues

Make sure to first use the search function to see if the bug has already been
reported.  When filling out a bug report, make sure that you include as much
information as possible to help the developers track down the issue, such as
your version of Panda3D, operating system, architecture, and any code and
models that are necessary for the developers to reproduce the issue.

If you're unsure whether you've encountered a bug, feel free to ask in the [forums](https://discourse.panda3d.org) or the [IRC channel](https://web.libera.chat/#panda3d) before opening an issue.


Supporting the Project
======================

If you would like to support the project financially, visit
[our campaign on OpenCollective](https://opencollective.com/panda3d).  Your
contributions help us accelerate the development of Panda3D.

For the list of backers, see the [BACKERS.md](BACKERS.md) file or visit the
[Sponsors page](https://www.panda3d.org/sponsors) on our web site.  Thank you
to everyone who has donated!

<a href="https://opencollective.com/panda3d" target="_blank">
  <img src="https://opencollective.com/panda3d/contribute/button@2x.png?color=blue" width=300 />
</a>
