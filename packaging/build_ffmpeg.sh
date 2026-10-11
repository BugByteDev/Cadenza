#!/usr/bin/env bash
set -euo pipefail
root=$(pwd)
mkdir -p build/runtime build/notices
if [ ! -d build/ffmpeg-source ]; then
 git clone --depth 1 --branch n8.0 https://github.com/FFmpeg/FFmpeg.git build/ffmpeg-source
fi
cd build/ffmpeg-source
./configure --disable-everything --disable-autodetect --disable-network --disable-doc --disable-debug --disable-x86asm --disable-shared --enable-static --enable-small --enable-ffmpeg --enable-protocol=file,pipe --enable-demuxer=mov,wav,pcm_s16le --enable-muxer=ipod,wav,pcm_s16le --enable-decoder=aac,pcm_s16le --enable-encoder=aac,pcm_s16le --enable-parser=aac --enable-filter=aresample,aformat,anull
make -j4
if [ -f ffmpeg.exe ]; then cp ffmpeg.exe "$root/build/runtime/"; else cp ffmpeg "$root/build/runtime/"; fi
cd "$root"
# Ship corresponding source and configuration beside every desktop package.
tar --exclude='.git' --exclude='*.o' --exclude='*.a' --exclude='ffmpeg' --exclude='ffmpeg.exe' --exclude='ffmpeg_g' -czf build/notices/FFmpeg-8.0-corresponding-source.tar.gz -C build ffmpeg-source
cp build/ffmpeg-source/COPYING.LGPLv2.1 build/notices/FFmpeg-LICENSE.txt
cp build/ffmpeg-source/ffbuild/config.log build/notices/FFmpeg-build-config.txt
