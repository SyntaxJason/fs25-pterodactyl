# The upstream image supplies Wine, Xvfb, Python, Mesa and the GIANTS runtime.
FROM toetje585/arch-fs25server@sha256:ba232f5bb58742b6ec63c8ba4cc64210ea9dbbd177c400fc828c6b8362be4ccb
USER root
# The published upstream image still contains Wine Staging 10.1. Use stable
# Wine 11 without upgrading the rest of the inherited Arch installation.
RUN curl -fsSL https://archive.archlinux.org/packages/w/wine/wine-11.0-1-x86_64.pkg.tar.zst -o /tmp/wine.pkg.tar.zst \
 && echo 'c93a939de66f3ddfa378b3ea2fb01f800477955f4cb623a81e94da1835b20c56  /tmp/wine.pkg.tar.zst' | sha256sum -c - \
 && pacman -Rdd --noconfirm wine-staging \
 && pacman -U --noconfirm /tmp/wine.pkg.tar.zst \
 && rm /tmp/wine.pkg.tar.zst
# Match packages to this image's Mesa version; do not partially upgrade Arch.
RUN curl -fsSL https://archive.archlinux.org/packages/x/xdotool/xdotool-3.20211022.1-2-x86_64.pkg.tar.zst -o /tmp/xdotool.pkg.tar.zst \
 && echo 'b22466e0bb2d17e11ce9e88f493de81e51eb5c6c6b09c7600ba4db40e357ae4e  /tmp/xdotool.pkg.tar.zst' | sha256sum -c - \
 && pacman -U --noconfirm /tmp/xdotool.pkg.tar.zst \
 && curl -fsSL https://archive.archlinux.org/packages/v/vulkan-swrast/vulkan-swrast-1%3A25.2.7-1-x86_64.pkg.tar.zst -o /tmp/vulkan.pkg.tar.zst \
 && echo '09d35657d913d53e1e67c7a0e8d675fdac86017f5967de8618dacf1095e53490  /tmp/vulkan.pkg.tar.zst' | sha256sum -c - \
 && curl -fsSL https://archive.archlinux.org/packages/v/vulkan-mesa-device-select/vulkan-mesa-device-select-1%3A25.2.7-1-x86_64.pkg.tar.zst -o /tmp/device-select.pkg.tar.zst \
 && echo '49aa118efe29d17c4f067dd49d8dc182b2503aec096435a422fa70f335c1c11c  /tmp/device-select.pkg.tar.zst' | sha256sum -c - \
 && pacman -U --noconfirm /tmp/device-select.pkg.tar.zst /tmp/vulkan.pkg.tar.zst \
 && rm /tmp/*.pkg.tar.zst
# Lavapipe in the matching Mesa package needs LLVM 21; keep the inherited LLVM
# 19 alongside it, since other preinstalled drivers still link against it.
RUN curl -fsSL https://archive.archlinux.org/packages/l/llvm-libs/llvm-libs-21.1.5-1-x86_64.pkg.tar.zst -o /tmp/llvm.pkg.tar.zst \
 && echo '0b6d562d825c921ca6050866820e30945c64304bf7bae7bd4bb2cae55cf04212  /tmp/llvm.pkg.tar.zst' | sha256sum -c - \
 && tar -xf /tmp/llvm.pkg.tar.zst -C / usr/lib/libLLVM.so.21.1 \
 && rm /tmp/llvm.pkg.tar.zst \
 && ! ldd /usr/lib/libvulkan_lvp.so | grep 'not found'
RUN curl -fsSL https://archive.archlinux.org/packages/7/7zip/7zip-25.01-1-x86_64.pkg.tar.zst -o /tmp/7zip.pkg.tar.zst \
 && echo 'a349b570ea102690d0f12094cabde3010266b4fd73a47c44c72d140b64a3b727  /tmp/7zip.pkg.tar.zst' | sha256sum -c - \
 && pacman -U --noconfirm /tmp/7zip.pkg.tar.zst \
 && rm /tmp/7zip.pkg.tar.zst \
 && for program in wine wineserver wineboot Xvfb xdotool 7z python; do command -v "$program"; done
RUN useradd --uid 988 --gid 988 --home-dir /home/container --create-home --shell /bin/bash container
# Der Entrypoint passt passwd/group an die vom Host vergebene UID an.
RUN chmod 666 /etc/passwd /etc/group
COPY runtime/ /opt/fs25-ptero/
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && python -m compileall -q /opt/fs25-ptero
ENV HOME=/home/container USER=container LOGNAME=container LANG=en_GB.UTF-8
USER container
WORKDIR /home/container
STOPSIGNAL SIGINT
# No supervisor, Firefox, VNC or noVNC is started.
ENTRYPOINT ["/entrypoint.sh"]
CMD []
