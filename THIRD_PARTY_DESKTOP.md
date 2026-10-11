# Desktop runtime notices

Desktop packages bundle Python/Tk, Node.js, Pygame/SDL, and a minimal FFmpeg 8.0 build in addition to Cadenza's separately licensed models and samples. Code licensing does not override any asset or runtime license. Retained notices and FFmpeg corresponding source/build configuration are in `_internal/notices`.

FFmpeg is a separate executable, built without GPL/nonfree options or third-party codecs, and distributed under LGPL 2.1 or later. Its source archive includes the exact checkout and generated configuration. Pygame is LGPL; its matching source archive and dependency build recipes are retained. Python, Tcl/Tk, Node.js and SDL retain their upstream licenses. PyInstaller's exception permits distributing packaged applications under their existing licenses. See the included source links for upstream dependency source and rebuild instructions.

To rebuild, install the pinned build dependencies, run `packaging/build_ffmpeg.sh`, then `python packaging/package_desktop.py`. Cadenza uses the bundled runtime executables first; replacing `_internal/runtime/node` or `_internal/runtime/ffmpeg` (or `.exe` on Windows) is supported.
