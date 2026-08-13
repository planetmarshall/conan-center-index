from conan import ConanFile, conan_version
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.android import android_abi
from conan.tools.apple import is_apple_os, to_apple_arch
from conan.tools.build import build_jobs, check_min_cppstd, cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import chdir, copy, get, load, replace_in_file, rm, rmdir, save, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, is_msvc_static_runtime, VCVars
from conan.tools.scm import Version
import configparser
import glob
from io import StringIO
import itertools
import os
import textwrap
import shutil

required_conan_version = ">=1.60.0 <2 || >=2.0.5"


# RDK Kirkstone ARMv7 Sky wayland plugin qmake project files. The vendored
# sources reference these exact generated protocol file names, so the .pro
# contents mirror setup_and_build_macos_kirkstone_qt563.sh verbatim.
_WL_SIMPLE_SHELL_PRO = """\
QT += waylandclient-private
TARGET = wl-simple-shell
TEMPLATE = lib
CONFIG += plugin c++11
DEFINES += QT_NO_DEBUG

INCLUDEPATH += .

SOURCES += \\
    main.cpp \\
    qwaylandwlsimpleshellintegration.cpp \\
    qwaylandwlsimpleshell.cpp \\
    qwaylandwlsimpleshellsurface.cpp \\
    qwaylandskyqshell.cpp \\
    qwayland-simple-shell.cpp \\
    qwayland-skyq-shell.cpp \\
    wayland-simple-shell-protocol.c \\
    wayland-skyq-shell-protocol.c

HEADERS += \\
    qt563logging.h \\
    qwaylandwlsimpleshellintegration_p.h \\
    qwaylandwlsimpleshell_p.h \\
    qwaylandwlsimpleshellsurface_p.h \\
    qwaylandskyqshell_p.h \\
    qwayland-simple-shell.h \\
    qwayland-skyq-shell.h \\
    wayland-simple-shell-client-protocol.h \\
    wayland-skyq-shell-client-protocol.h

OTHER_FILES += wl-simple-shell.json

PLUGIN_TYPE = wayland-shell-integration
load(qt_plugin)
"""

_SKYQ_INPUT_PRO = """\
QT += waylandclient-private
TARGET = skyq-input
TEMPLATE = lib
CONFIG += plugin c++11
DEFINES += QT_NO_DEBUG

INCLUDEPATH += .

SOURCES += \\
    main.cpp \\
    qwaylandskyqinputdeviceintegration.cpp \\
    qwaylandskyqinput.cpp \\
    qwaylandnullinputdevice.cpp \\
    qwayland-skyq-input.cpp \\
    wayland-skyq-input-protocol.c

HEADERS += \\
    qt563logging.h \\
    qwaylandskyqinputdeviceintegration_p.h \\
    qwaylandskyqinput.h \\
    qwaylandnullinputdevice.h \\
    qwayland-skyq-input.h \\
    wayland-skyq-input-client-protocol.h \\
    ethannativeevent.h

OTHER_FILES += skyq-input.json

PLUGIN_TYPE = wayland-inputdevice-integration
load(qt_plugin)
"""


class QtConan(ConanFile):
    _submodules = ["qtsvg", "qtdeclarative", "qtactiveqt", "qtscript", "qtmultimedia", "qttools", "qtxmlpatterns",
    "qttranslations", "qtdoc", "qtlocation", "qtsensors", "qtconnectivity", "qtwayland",
    "qt3d", "qtimageformats", "qtgraphicaleffects", "qtquickcontrols", "qtserialbus", "qtserialport", "qtx11extras",
    "qtmacextras", "qtwinextras", "qtandroidextras", "qtwebsockets", "qtwebchannel", "qtwebengine", "qtwebview",
    "qtquickcontrols2", "qtpurchasing", "qtcharts", "qtdatavis3d", "qtvirtualkeyboard", "qtgamepad", "qtscxml",
    "qtspeech", "qtnetworkauth", "qtremoteobjects", "qtwebglplugin", "qtlottie", "qtquicktimeline", "qtquick3d",
    "qtknx", "qtmqtt", "qtcoap", "qtopcua"]

    _module_statuses = ["essential", "addon", "deprecated", "preview"]

    name = "qt"
    description = "Qt is a cross-platform framework for graphical user interfaces."
    topics = ("ui", "framework")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.qt.io"
    license = "LGPL-2.1-only"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "commercial": [True, False],

        "opengl": ["no", "es2", "desktop", "dynamic"],
        "with_vulkan": [True, False],
        "openssl": [True, False],
        "with_pcre2": [True, False],
        "with_glib": [True, False],
        # "with_libiconv": [True, False],  # QTBUG-84708 Qt tests failure "invalid conversion from const char** to char**"
        "with_doubleconversion": [True, False],
        "with_freetype": [True, False],
        "with_fontconfig": [True, False],
        "with_icu": [True, False],
        "with_harfbuzz": [True, False],
        "with_libjpeg": ["libjpeg", "libjpeg-turbo", False],
        "with_libpng": [True, False],
        "with_sqlite3": [True, False],
        "with_mysql": ["mysql", "mariadb", False],
        "with_pq": [True, False],
        "with_odbc": [True, False],
        "with_libalsa": [True, False],
        "with_openal": [True, False],
        "with_zstd": [True, False],
        "with_gstreamer": [True, False],
        "with_pulseaudio": [True, False],
        "with_dbus": [True, False],
        "with_gssapi": [True, False],
        "with_atspi": [True, False],
        "with_md4c": [True, False],
        "with_x11": [True, False],

        "gui": [True, False],
        "widgets": [True, False],

        "android_sdk": [None, "ANY"],
        "device": [None, "ANY"],
        "cross_compile": [None, "ANY"],
        "sysroot": [None, "ANY"],
        "config": [None, "ANY"],
        "multiconfiguration": [True, False]
    }
    options.update({module: [True, False] for module in _submodules})
    options.update({f"{status}_modules": [True, False] for status in _module_statuses})

    default_options = {
        "shared": False,
        "commercial": False,
        "opengl": "desktop",
        "with_vulkan": False,
        "openssl": True,
        "with_pcre2": True,
        "with_glib": False,
        # "with_libiconv": True, # QTBUG-84708
        "with_doubleconversion": True,
        "with_freetype": True,
        "with_fontconfig": True,
        "with_icu": True,
        "with_harfbuzz": False,
        "with_libjpeg": "libjpeg",
        "with_libpng": True,
        "with_sqlite3": True,
        "with_mysql": "mysql",
        "with_pq": True,
        "with_odbc": True,
        "with_libalsa": False,
        "with_openal": True,
        "with_zstd": True,
        "with_gstreamer": False,
        "with_pulseaudio": False,
        "with_dbus": False,
        "with_gssapi": False,
        "with_atspi": False,
        "with_md4c": True,
        "with_x11": True,

        "gui": True,
        "widgets": True,

        "android_sdk": None,
        "device": None,
        "cross_compile": None,
        "sysroot": None,
        "config": None,
        "multiconfiguration": False,
    }
    # essential_modules, addon_modules, deprecated_modules, preview_modules:
    #    these are only provided for convenience, set to False by default
    default_options.update({f"{status}_modules": False for status in _module_statuses})

    no_copy_source = True
    short_paths = True

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    @property
    def _is_rdk_kirkstone(self):
        # True when cross-building for the RDK Kirkstone ARMv7 target, gated on the
        # os.rdk subsetting provided by the entos-rdk-kirkstone-armv7 profile.
        # Mirrors setup_and_build_macos_kirkstone_qt563.sh.
        return self.settings.os == "Linux" and self.settings.get_safe("os.rdk") == "kirkstone"

    @property
    def _rdk_toolchain_bin(self):
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = execs.get("c")
        return os.path.dirname(cc) if cc else None

    @property
    def _rdk_cross_prefix(self):
        # e.g. "arm-rdk-linux-gnueabi-" derived from the profile's C compiler name.
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = os.path.basename(execs.get("c", "")) if execs.get("c") else ""
        if cc.endswith("gcc"):
            return cc[:-3]
        return "arm-rdk-linux-gnueabi-"

    def export(self):
        copy(self, f"qtmodules{self.version}.conf", self.recipe_folder, self.export_folder)
        # 5.6.3: install-side changes from the core-app setup_and_build Qt SDK
        # pipeline, applied manually in package() so the Conan build reproduces
        # the local_sdk SDK exactly. (The source patch is a conandata patch.)
        copy(self, "qt563_install.patch", self.recipe_folder, self.export_folder)
        # 5.6.3 Linux: sources for the OSMesa-based offscreen GL platform plugin,
        # built and packaged in package() so QT_QPA_PLATFORM=offscreengl works
        # headless (mirrors setup_and_build_linux_x86_qt563.sh).
        copy(self, "*", os.path.join(self.recipe_folder, "addons", "offscreengl-src"),
             os.path.join(self.export_folder, "addons", "offscreengl-src"))
        # 5.6.3 RDK Kirkstone ARMv7: wayland source patch plus the vendored stub
        # and plugin sources cross-compiled in package(), mirroring
        # setup_and_build_macos_kirkstone_qt563.sh (neon-lib, libproxy, wayland).
        copy(self, "qt563_wayland.patch", self.recipe_folder, self.export_folder)
        for addon in ("stubs", "wl-simple-shell-src", "skyq-input-src"):
            copy(self, "*", os.path.join(self.recipe_folder, "addons", addon),
                 os.path.join(self.export_folder, "addons", addon))

    def export_sources(self):
        export_conandata_patches(self)

    def validate_build(self):
        if self.options.qtwebengine:
            # Check if a valid python2 is available in PATH or it will failflex
            # Start by checking if python2 can be found
            python_exe = shutil.which("python2")
            if not python_exe:
                # Fall back on regular python
                python_exe = shutil.which("python")

            if not python_exe:
                msg = ("Python2 must be available in PATH "
                       "in order to build Qt WebEngine")
                raise ConanInvalidConfiguration(msg)

            # In any case, check its actual version for compatibility
            command_output = StringIO()
            cmd_v = f"\"{python_exe}\" -c \"import platform;print(platform.python_version())\""
            self.run(cmd_v, command_output)
            verstr = command_output.getvalue().strip()
            version = Version(verstr)
            # >= 2.7.5 & < 3
            v_min = "2.7.5"
            v_max = "3.0.0"
            if (version >= v_min) and (version < v_max):
                msg = ("Found valid Python 2 required for QtWebengine:"
                       f" version={verstr}, path={python_exe}")
                self.output.success(msg)
            else:
                msg = (f"Found Python 2 in path, but with invalid version {verstr}"
                       f" (QtWebEngine requires >= {v_min} & < {v_max})\n"
                       "If you have both Python 2 and 3 installed, copy the python 2 executable to"
                       "python2(.exe)")
                raise ConanInvalidConfiguration(msg)

    def config_options(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_icu
            del self.options.with_fontconfig
            del self.options.with_libalsa
            del self.options.with_x11
            del self.options.qtx11extras
        if self.settings.compiler == "apple-clang":
            if Version(self.settings.compiler.version) < "10.0":
                raise ConanInvalidConfiguration("Old versions of apple sdk are not supported by Qt (QTBUG-76777)")
        if self.settings.compiler in ["gcc", "clang"]:
            if Version(self.settings.compiler.version) < "5.0":
                raise ConanInvalidConfiguration("qt 5.15.X does not support GCC or clang before 5.0")
        if self.settings.compiler in ["gcc", "clang"] and Version(self.settings.compiler.version) < "5.3":
            del self.options.with_mysql
        if self.settings.os == "Windows":
            self.options.opengl = "dynamic"
            del self.options.with_gssapi
        if self.settings.os != "Linux":
            self.options.qtwayland = False
            self.options.with_atspi = False

        if self.settings.os != "Windows":
            del self.options.qtwinextras
            del self.options.qtactiveqt

        if self.settings.os != "Macos":
            del self.options.qtmacextras

        if self.settings.os != "Android":
            del self.options.android_sdk

        # Disable features that didn't exist or have incompatible dependencies
        del self.options.openssl
        del self.options.with_pcre2
        del self.options.with_md4c
        del self.options.with_zstd
        del self.options.with_harfbuzz
        del self.options.with_mysql
        del self.options.with_pq
        del self.options.with_odbc
        # Use Qt bundled versions to avoid old dependency version issues
        del self.options.with_doubleconversion
        del self.options.with_freetype
        del self.options.with_libjpeg
        del self.options.with_libpng
        del self.options.with_sqlite3

        # RDK Kirkstone ARMv7 target: the device renders through wayland-egl on
        # GLES2 and has no X11. Force the same configuration the local_sdk build
        # produces (setup_and_build_macos_kirkstone_qt563.sh) so the packaged Qt
        # is drop-in compatible: GLES2, no xcb, and qtwayland (client + platform
        # plugins) built as part of the Qt build.
        if self._is_rdk_kirkstone:
            self.options.opengl = "es2"
            self.options.with_x11 = False
            self.options.qtwayland = True

    def _debug_output(self, message):
        if Version(conan_version) >= "2":
            self.output.debug(message)

    def configure(self):
        # if self.settings.os != "Linux":
        #         self.options.with_libiconv = False # QTBUG-84708

        if not self.options.gui:
            self.options.rm_safe("opengl")
            self.options.rm_safe("with_vulkan")
            self.options.rm_safe("with_freetype")
            self.options.rm_safe("with_fontconfig")
            self.options.rm_safe("with_harfbuzz")
            self.options.rm_safe("with_libjpeg")
            self.options.rm_safe("with_libpng")
            self.options.rm_safe("with_md4c")
            self.options.rm_safe("with_x11")

        if not self.options.with_dbus:
            self.options.rm_safe("with_atspi")

        if self.options.multiconfiguration:
            del self.settings.build_type

        config = configparser.ConfigParser()
        config.read(os.path.join(self.recipe_folder, f"qtmodules{self.version}.conf"))
        submodules_tree = {}
        assert config.sections(), f"no qtmodules.conf file for version {self.version}"
        for s in config.sections():
            section = str(s)
            assert section.startswith("submodule ")
            assert section.count('"') == 2
            modulename = section[section.find('"') + 1: section.rfind('"')]
            status = str(config.get(section, "status"))
            if status not in ("obsolete", "ignore"):
                if status not in self._module_statuses:
                    raise ConanException(f"module {modulename} has status {status} which is not in self._module_statuses {self._module_statuses}")
                submodules_tree[modulename] = {"status": status,
                                "path": str(config.get(section, "path")), "depends": []}
                if config.has_option(section, "depends"):
                    submodules_tree[modulename]["depends"] = [str(i) for i in config.get(section, "depends").split()]

        for m in submodules_tree:
            assert m in ["qtbase", "qtqa", "qtrepotools"] or m in self._submodules, "module %s is not present in recipe options : (%s)" % (m, ",".join(self._submodules))

        # Store valid modules for this version to use in build()
        self._valid_modules = set(submodules_tree.keys())

        for module in self._submodules:
            if module not in submodules_tree:
                self._debug_output(f"qt5: removing {module} from options as it is not an option for this version, or it is ignored or obsolete")
                self.options.rm_safe(module)

        # Requested modules:
        # - any module for non-removed options that have 'True' value
        # - any enabled via `xxx_modules` that does not have a 'False' value
        # Note that at this point, the submodule options dont have a value unless one is given externally
        # to the recipe (e.g. via the command line, a profile, or a consumer)
        requested_modules = set([module for module in self._submodules if self.options.get_safe(module)])
        for module in [m for m in self._submodules if m in submodules_tree]:
            status = submodules_tree[module]['status']
            is_disabled = self.options.get_safe(module) == False
            if self.options.get_safe(f"{status}_modules"):
                if not is_disabled:
                    requested_modules.add(module)
                else:
                    self.output.warning(f"qt5: {module} requested because {status}_modules=True"
                                        f" but it has been explicitly disabled with {module}=False")

        self.output.info(f"qt5: requested modules {list(requested_modules)}")

        required_modules = {}
        for module in requested_modules:
            deps = submodules_tree[module]["depends"]
            for dep in deps:
                required_modules.setdefault(dep,[]).append(module)

        required_but_disabled = [m for m in required_modules.keys() if self.options.get_safe(m) == False]
        if required_modules:
            self._debug_output(f"qt5: required_modules modules {list(required_modules.keys())}")
        if required_but_disabled:
            required_by = set()
            for m in required_but_disabled:
                required_by.update(required_modules[m])
                raise ConanInvalidConfiguration(f"Modules {required_but_disabled} are explicitly disabled, "
                                    f"but are required by {list(required_by)}, enabled by other options")

        enabled_modules = requested_modules.union(set(required_modules.keys()))
        enabled_modules.discard("qtbase")

        for module in list(enabled_modules):
            setattr(self.options, module, True)

        for module in self._submodules:
            if module in self.options and not self.options.get_safe(module):
                setattr(self.options, module, False)

        if not self.options.qtmultimedia:
            self.options.rm_safe("with_libalsa")
            del self.options.with_openal
            del self.options.with_gstreamer
            del self.options.with_pulseaudio

        if self.settings.os in ("FreeBSD", "Linux"):
            if self.options.qtwebengine:
                self.options.with_fontconfig = True

        for status in self._module_statuses:
            # These are convenience only, should not affect package_id
            option_name = f"{status}_modules"
            self._debug_output(f"qt5 removing convenience option: {option_name},"
                              f" see individual module options")
            self.options.rm_safe(option_name)

        for option in self.options.items():
            self._debug_output(f"qt5 option {option[0]}={option[1]}")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")
        if self.options.widgets and not self.options.gui:
            raise ConanInvalidConfiguration("using option qt:widgets without option qt:gui is not possible. "
                                            "You can either disable qt:widgets or enable qt:gui")

        if self.options.qtwebengine:
            if not self.options.shared:
                raise ConanInvalidConfiguration("Static builds of Qt WebEngine are not supported")
            if not (self.options.gui and self.options.qtdeclarative and self.options.qtlocation and self.options.qtwebchannel):
                raise ConanInvalidConfiguration("option qt:qtwebengine requires also qt:gui, qt:qtdeclarative, qt:qtlocation and qt:qtwebchannel")

            if hasattr(self, "settings_build") and cross_building(self, skip_x64_x86=True):
                raise ConanInvalidConfiguration("Cross compiling Qt WebEngine is not supported")

            if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
                raise ConanInvalidConfiguration("Compiling Qt WebEngine with gcc < 5 is not supported")

        if self.settings.os == "Android":
            if self.options.get_safe("opengl", "no") == "desktop":
                raise ConanInvalidConfiguration("OpenGL desktop is not supported on Android. Consider using OpenGL es2")
            if not self.options.get_safe("android_sdk", ""):
                raise ConanInvalidConfiguration("Path to Android SDK is required to build Qt")

        if self.settings.os != "Windows" and self.options.get_safe("opengl", "no") == "dynamic":
            raise ConanInvalidConfiguration("Dynamic OpenGL is supported only on Windows.")

        if self.options.get_safe("with_fontconfig", False) and not self.options.get_safe("with_freetype", False):
            raise ConanInvalidConfiguration("with_fontconfig cannot be enabled if with_freetype is disabled.")

        if self.options.get_safe("with_doubleconversion", True) is False and self.settings.get_safe("compiler.libcxx") != "libc++":
            raise ConanInvalidConfiguration("Qt without libc++ needs qt:with_doubleconversion. "
                                            "Either enable qt:with_doubleconversion or switch to libc++")

        if is_msvc_static_runtime(self) and self.options.shared:
            raise ConanInvalidConfiguration("Qt cannot be built as shared library with static runtime")

        if self.settings.compiler == "apple-clang":
            if Version(self.settings.compiler.version) < "10.0":
                raise ConanInvalidConfiguration("Old versions of apple sdk are not supported by Qt (QTBUG-76777)")
        if self.settings.compiler in ["gcc", "clang"]:
            if Version(self.settings.compiler.version) < "5.0":
                raise ConanInvalidConfiguration("qt 5.15.X does not support GCC or clang before 5.0")

        if self.options.get_safe("with_pulseaudio", default=False) and not self.dependencies["pulseaudio"].options.with_glib:
            # https://bugreports.qt.io/browse/QTBUG-95952
            raise ConanInvalidConfiguration("Pulseaudio needs to be built with glib option or qt's configure script won't detect it")

        if self.options.get_safe("with_x11", False) and not self.dependencies.direct_host["xkbcommon"].options.with_x11:
            raise ConanInvalidConfiguration("The 'with_x11' option for the 'xkbcommon' package must be enabled when the 'with_x11' option is enabled")
        if self.options.get_safe("qtwayland", False) and not self.dependencies.direct_host["xkbcommon"].options.with_wayland:
            raise ConanInvalidConfiguration("The 'with_wayland' option for the 'xkbcommon' package must be enabled when the 'qtwayland' option is enabled")

        if cross_building(self) and self.options.cross_compile == "None" and not is_apple_os(self) and self.settings.os != "Android":
            raise ConanInvalidConfiguration("option cross_compile must be set for cross compilation "
                                            "cf https://doc.qt.io/qt-5/configure-options.html#cross-compilation-options")

        if self.options.get_safe("with_sqlite3", False) and not self.dependencies["sqlite3"].options.enable_column_metadata:
            raise ConanInvalidConfiguration("sqlite3 option enable_column_metadata must be enabled for qt")

    def requirements(self):
        self.requires("zlib/[>=1.2.11 <2]")
        # Linux/FreeBSD have no native TLS backend, so Qt is linked against
        # OpenSSL there (see build() -openssl-linked). Apple uses SecureTransport.
        if self.options.get_safe("openssl", False) or self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("openssl/[>=1.1 <4]")
        if self.options.get_safe("with_pcre2", False):
            self.requires("pcre2/[>=10.42 <11]")
        if self.options.get_safe("with_vulkan"):
            self.requires("vulkan-loader/1.3.268.0")
            if is_apple_os(self):
                self.requires("moltenvk/1.2.2")
        if self.options.with_glib:
            self.requires("glib/2.78.3")
        # if self.options.with_libiconv: # QTBUG-84708
        #     self.requires("libiconv/1.16")# QTBUG-84708
        if self.options.get_safe("with_doubleconversion", False) and not self.options.multiconfiguration:
            self.requires("double-conversion/3.3.0")
        if self.options.get_safe("with_freetype", False) and not self.options.multiconfiguration:
            self.requires("freetype/[>=2.13 <3]")
        if self.options.get_safe("with_fontconfig", False):
            self.requires("fontconfig/2.15.0")
        if self.options.get_safe("with_icu", False):
            self.requires("icu/74.2")
        if self.options.get_safe("with_harfbuzz", False) and not self.options.multiconfiguration:
            self.requires("harfbuzz/[>=8.3.0]")
        if self.options.get_safe("with_libjpeg", False) and not self.options.multiconfiguration:
            if self.options.get_safe("with_libjpeg", False) == "libjpeg-turbo":
                self.requires("libjpeg-turbo/2.1.5")
            else:
                self.requires("libjpeg/9d")
        if (
            self.options.get_safe("with_libpng", False)
            and not self.options.multiconfiguration
        ):
            self.requires("libpng/[>=1.6 <2]")
        if self.options.get_safe("with_sqlite3", False) and not self.options.multiconfiguration:
            self.requires("sqlite3/[>=3.45.0 <4]")
        if self.options.get_safe("with_mysql", False) == "mariadb":
            self.requires("mariadb-connector-c/3.3.3")
        if self.options.get_safe("with_openal", False):
            self.requires("openal-soft/[>=1.22.2 <2]")
        if self.options.get_safe("with_libalsa", False):
            self.requires("libalsa/1.2.10")
        if self.options.get_safe("with_x11"):
            self.requires("xorg/system")
        if self.options.get_safe("with_x11") or self.options.qtwayland:
            self.requires("xkbcommon/[>=1.5.0 <2]")
        if self.options.get_safe("opengl", "no") != "no":
            self.requires("opengl/system")
        if self.options.get_safe("with_zstd", False):
            self.requires("zstd/[>=1.5 <1.6]")
        if self.options.qtwebengine and self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("expat/[>=2.6.2 <3]")
            self.requires("opus/1.4")
            if not self.options.qtwayland:
                self.requires("xorg-proto/2022.2")
            self.requires("libxshmfence/1.3")
            self.requires("nss/3.93")
            self.requires("libdrm/[>=2.4.119 <3]")
            self.requires("egl/system")
        if self.options.get_safe("with_gstreamer", False):
            self.requires("gst-plugins-base/1.19.2")
        if self.options.get_safe("with_pulseaudio", False):
            self.requires("pulseaudio/[>=14.2 <20]")
        if self.options.with_dbus:
            self.requires("dbus/1.15.8")
        if self.options.qtwayland:
            self.requires("wayland/1.22.0")
        if self.settings.os in ['Linux', 'FreeBSD'] and self.options.with_gssapi:
            self.requires("krb5/1.21.2")
        if self.options.get_safe("with_atspi"):
            self.requires("at-spi2-core/2.51.0")
        if self.options.get_safe("with_md4c", False):
            self.requires("md4c/[>=0.4.8 <1]")

    def package_id(self):
        del self.info.options.cross_compile
        del self.info.options.sysroot
        if self.info.options.multiconfiguration:
            if self.info.settings.compiler == "Visual Studio":
                if "MD" in self.info.settings.compiler.runtime:
                    self.info.settings.compiler.runtime = "MD/MDd"
                else:
                    self.info.settings.compiler.runtime = "MT/MTd"
            elif self.info.settings.compiler == "msvc":
                self.info.settings.compiler.runtime_type = "Release/Debug"
        if self.info.settings.os == "Android":
            del self.info.options.android_sdk

    def build_requirements(self):
        if self._settings_build.os == "Windows" and is_msvc(self):
            self.tool_requires("jom/[>=1.1 <2]")
        if self.options.qtwebengine:
            self.tool_requires("ninja/[>=1.12 <2]")
            self.tool_requires("nodejs/18.15.0")
            self.tool_requires("gperf/3.1")
            # gperf, bison, flex, python >= 2.7.5 & < 3
            if self._settings_build.os == "Windows":
                self.tool_requires("winflexbison/2.5.25")
            else:
                self.tool_requires("bison/3.8.2")
                self.tool_requires("flex/2.6.4")
        if self.options.qtwayland:
            self.tool_requires("wayland/<host_version>")

    @property
    def angle_path(self):
        return os.path.join(self.source_folder, "angle")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True, destination="qt5")

        apply_conandata_patches(self)

        # shorten the path to ANGLE to avoid the following error:
        # C:\J2\w\prod-v2\bsr@4\104220\ebfcf\p\qtde01f793a6074\s\qt5\qtbase\src\3rdparty\angle\src\libANGLE\renderer\d3d\d3d11\texture_format_table_autogen.cpp : fatal error C1083: Cannot open compiler generated file: '': Invalid argument
        copy(self, "*", os.path.join(self.source_folder, "qt5", "qtbase", "src", "3rdparty", "angle"), self.angle_path)

    def generate(self):
        pc = PkgConfigDeps(self)
        pc.generate()
        ms = VCVars(self)
        ms.generate()
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        if not cross_building(self,  skip_x64_x86=self.settings.os == "Windows"):
            vre = VirtualRunEnv(self)
            vre.generate(scope="build")
        env = Environment()
        env.define("MAKEFLAGS", f"j{build_jobs(self)}")
        env.define("ANGLE_DIR", self.angle_path)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # Qt 5.6.3's -openssl-linked config test/link must find the Conan OpenSSL
        # libraries, which live in the Conan cache rather than a system path. The
        # configure script honours OPENSSL_LIBS; include dirs come from the global
        # -I injection below (direct_host deps).
        if self.settings.os in ["Linux", "FreeBSD"]:
            _ossl = self.dependencies["openssl"].cpp_info.aggregated_components()
            _ossl_flags = [f"-L{d}" for d in _ossl.libdirs] + [f"-l{l}" for l in _ossl.libs]
            env.define("OPENSSL_LIBS", " ".join(_ossl_flags))
        if self.settings.os == "Windows":
            env.prepend_path("PATH", os.path.join(self.source_folder, "qt5", "gnuwin32", "bin"))
        if is_apple_os(self):
            # Reproduce setup_and_build_macos_desktop_qt563.sh on Apple Silicon:
            # force the target arch and disable NEON, since Qt 5.6.3 only wires
            # NEON drawhelpers for Linux/Android and references undefined symbols
            # on macOS arm64 otherwise.
            apple_arch = to_apple_arch(self)
            arch_flags = f"-arch {apple_arch} -U__ARM_NEON__ -U__ARM_NEON"
            env.define("CC", "clang")
            env.define("CXX", "clang++")
            env.define("CFLAGS", arch_flags)
            env.define("CXXFLAGS", arch_flags)
            env.define("LDFLAGS", f"-arch {apple_arch}")
        if self._is_rdk_kirkstone:
            # Put the RDK cross-toolchain bin dir first on PATH so qmake finds the
            # arm-rdk-linux-gnueabi-* tools named by the retargeted target mkspec.
            # Deliberately do NOT export CC/CXX: that would make the recipe set
            # QMAKE_CC/QMAKE_CXX globally and force Qt's host bootstrap tools
            # (native linux-g++, no --sysroot) to use the cross compiler, which
            # then cannot find its sysroot-hosted C++ headers (<cstddef>). The
            # cross compiler is scoped to the target via the mkspec's CROSS_COMPILE
            # prefix instead, exactly like setup_and_build_macos_kirkstone_qt563.sh.
            tc_bin = self._rdk_toolchain_bin
            if tc_bin:
                env.prepend_path("PATH", tc_bin)
            # The RDK profile's [buildenv] exports Yocto/autotools toolchain
            # variables (LD, LDFLAGS, AR, RANLIB, STRIP, OBJDUMP). Qt 5.6.3's
            # configure imports this exact set of SYSTEM_VARIABLES from the
            # environment into .qmake.cache (LD -> QMAKE_LINK, LDFLAGS ->
            # QMAKE_LFLAGS, AR -> QMAKE_AR, ...), which is loaded globally for
            # every build including the host bootstrap tools. That pins
            # QMAKE_LINK to the bare cross `ld` and QMAKE_LFLAGS to `-Wl,-O1`
            # (a compiler-driver flag the bare linker rejects), so moc/uic fail
            # to link. The from-source setup_and_build_macos_kirkstone_qt563.sh
            # has none of these in its environment. Unset them so Qt resolves
            # the linker/archiver from the mkspec instead: native for the host
            # bootstrap tools, CROSS_COMPILE-prefixed for the target.
            for _sysvar in ("LD", "LDFLAGS", "AR", "RANLIB", "STRIP", "OBJDUMP"):
                env.unset(_sysvar)
        # qtdeclarative (QtQml / bundled JavaScriptCore) invokes a `python`
        # executable at build time; on hosts that only ship `python3` qmake
        # aborts with "Building QtQml requires Python". Provide a python->python3
        # shim on PATH, matching the setup_and_build_*_qt563.sh scripts.
        if not shutil.which("python") and shutil.which("python3"):
            python_shim_dir = os.path.join(self.build_folder, ".python-shim")
            shim = os.path.join(python_shim_dir, "python")
            save(self, shim, '#!/usr/bin/env bash\nexec "%s" "$@"\n' % shutil.which("python3"))
            os.chmod(shim, 0o755)
            env.prepend_path("PATH", python_shim_dir)
        env.vars(self).save_script("conan_qt_env_file")

    def _make_program(self):
        if is_msvc(self):
            return "jom"
        elif self._settings_build.os == "Windows":
            return "mingw32-make"
        else:
            return "make"

    def _xplatform(self):
        if self.settings.os == "Linux":
            if self.settings.compiler == "gcc":
                return {"x86": "linux-g++-32",
                        "armv6": "linux-arm-gnueabi-g++",
                        "armv7": "linux-arm-gnueabi-g++",
                        "armv7hf": "linux-arm-gnueabi-g++",
                        "armv8": "linux-aarch64-gnu-g++"}.get(str(self.settings.arch), "linux-g++")
            elif self.settings.compiler == "clang":
                if self.settings.arch == "x86":
                    return "linux-clang-libc++-32" if self.settings.compiler.libcxx == "libc++" else "linux-clang-32"
                elif self.settings.arch == "x86_64":
                    return "linux-clang-libc++" if self.settings.compiler.libcxx == "libc++" else "linux-clang"

        elif self.settings.os == "Macos":
            return {"clang": "macx-clang",
                    "apple-clang": "macx-clang",
                    "gcc": "macx-g++"}.get(str(self.settings.compiler))

        elif self.settings.os == "iOS":
            if self.settings.compiler == "apple-clang":
                return "macx-ios-clang"

        elif self.settings.os == "watchOS":
            if self.settings.compiler == "apple-clang":
                return "macx-watchos-clang"

        elif self.settings.os == "tvOS":
            if self.settings.compiler == "apple-clang":
                return "macx-tvos-clang"

        elif self.settings.os == "Android":
            if self.settings.compiler == "clang":
                return "android-clang"

        elif self.settings.os == "Windows":
            return {
                "Visual Studio": "win32-msvc",
                "msvc": "win32-msvc",
                "gcc": "win32-g++",
                "clang": "win32-clang-g++",
            }.get(str(self.settings.compiler))

        elif self.settings.os == "WindowsStore":
            if is_msvc(self):
                if str(self.settings.compiler) == "Visual Studio":
                    msvc_version = str(self.settings.compiler.version)
                else:
                    msvc_version = {
                        "190": "14",
                        "191": "15",
                        "192": "16",
                    }.get(str(self.settings.compiler.version))
                return {
                    "14": {
                        "armv7": "winrt-arm-msvc2015",
                        "x86": "winrt-x86-msvc2015",
                        "x86_64": "winrt-x64-msvc2015",
                    },
                    "15": {
                        "armv7": "winrt-arm-msvc2017",
                        "x86": "winrt-x86-msvc2017",
                        "x86_64": "winrt-x64-msvc2017",
                    },
                    "16": {
                        "armv7": "winrt-arm-msvc2019",
                        "x86": "winrt-x86-msvc2019",
                        "x86_64": "winrt-x64-msvc2019",
                        },
                    }.get(msvc_version).get(str(self.settings.arch))

        elif self.settings.os == "FreeBSD":
            return {"clang": "freebsd-clang",
                    "gcc": "freebsd-g++"}.get(str(self.settings.compiler))

        elif self.settings.os == "SunOS":
            if self.settings.compiler == "sun-cc":
                if self.settings.arch == "sparc":
                    return "solaris-cc-stlport" if self.settings.compiler.libcxx == "libstlport" else "solaris-cc"
                elif self.settings.arch == "sparcv9":
                    return "solaris-cc64-stlport" if self.settings.compiler.libcxx == "libstlport" else "solaris-cc64"
            elif self.settings.compiler == "gcc":
                return {"sparc": "solaris-g++",
                        "sparcv9": "solaris-g++-64"}.get(str(self.settings.arch))
        elif self.settings.os == "Neutrino" and self.settings.compiler == "qcc":
            return {"armv8": "qnx-aarch64le-qcc",
                    "armv8.3": "qnx-aarch64le-qcc",
                    "armv7": "qnx-armle-v7-qcc",
                    "armv7hf": "qnx-armle-v7-qcc",
                    "armv7s": "qnx-armle-v7-qcc",
                    "armv7k": "qnx-armle-v7-qcc",
                    "x86": "qnx-x86-qcc",
                    "x86_64": "qnx-x86-64-qcc"}.get(str(self.settings.arch))
        elif self.settings.os == "Emscripten" and self.settings.arch == "wasm":
            return "wasm-emscripten"

        return None

    def build(self):
        if self.settings.os == "Macos":
            configure_script = os.path.join(
                self.source_folder, "qt5", "qtbase", "configure"
            )
            # strict=False: with no_copy_source=True these edits mutate the shared
            # source tree, so a rebuild/restart may see them already applied.
            replace_in_file(
                self,
                configure_script,
                "CFG_USE_GOLD_LINKER=auto\nCFG_ENABLE_NEW_DTAGS=auto",
                "CFG_USE_GOLD_LINKER=no\nCFG_ENABLE_NEW_DTAGS=no",
                strict=False,
            )
            replace_in_file(
                self,
                configure_script,
                "if linkerSupportsFlag $TEST_COMPILER --enable-new-dtags; then",
                "if false; then  # Disabled for macOS",
                strict=False,
            )
            # NOTE: the mac.conf OpenGL/AGL fix is applied by qt563_source.patch.
        if self._is_rdk_kirkstone:
            # Apply the qtwayland compatibility patch (wl_keyboard v4 repeat_info,
            # stale-pointer guard) to the shared source, matching the wayland step
            # of setup_and_build_macos_kirkstone_qt563.sh. --forward makes it
            # idempotent across rebuilds with no_copy_source.
            wl_patch = os.path.join(self.recipe_folder, "qt563_wayland.patch")
            qt_src = os.path.join(self.source_folder, "qt5")
            self.run(f'patch -p1 --batch --forward --ignore-whitespace -d "{qt_src}" < "{wl_patch}" || true')
            # Strip the RDK sysroot's Qt 5.15 link-time symlinks (libQt5*.so /
            # .so.5 / .so.5.6* / *_ours) so the cross-linker cannot resolve -lQt5X
            # against the sysroot Qt 5.15 and mix its @Qt_5[_PRIVATE_API] symbols
            # into the freshly built Qt 5.6.3 (the failure breaks qtdeclarative's
            # ordered build, so every module after it, e.g. qtwebsockets, is never
            # built). Mirrors the inject step of setup_and_build_macos_kirkstone_qt563.sh;
            # the real versioned libQt5*.so.5.15.* files are left intact.
            rdk_sysroot = self.conf.get("tools.build:sysroot", check_type=str)
            if rdk_sysroot:
                sysroot_lib = os.path.join(rdk_sysroot, "usr", "lib")
                removed = 0
                for _pattern in ("libQt5*.so", "libQt5*.so.5", "libQt5*_ours", "libQt5*.so.5.6*"):
                    for _link in glob.glob(os.path.join(sysroot_lib, _pattern)):
                        if os.path.islink(_link):
                            os.unlink(_link)
                            removed += 1
                if removed:
                    self.output.info(f"RDK: removed {removed} Qt 5.15 link-time symlink(s) "
                                     f"from sysroot lib dir {sysroot_lib}")
        args = ["-confirm-license", "-silent", "-nomake examples", "-nomake tests",
                f"-prefix {self.package_folder}"]
        args.append("-no-warnings-are-errors")
        # Match core-app setup_and_build Qt 5.6.3 configure flags.
        args.append("-no-pch")
        args.append("-no-qml-debug")
        if is_apple_os(self):
            # Apple Silicon: NEON disabled via CFLAGS (-U__ARM_NEON__); ensure
            # Qt does not enable x86 SIMD paths either.
            args += ["-no-sse2", "-no-sse3", "-no-ssse3",
                     "-no-sse4.1", "-no-sse4.2", "-no-avx", "-no-avx2"]
        # Match core-app setup_and_build reference: don't build the deprecated
        # Enginio module (the reference passes -skip qtenginio).
        if os.path.isdir(os.path.join(self.source_folder, "qt5", "qtenginio")):
            args.append("-skip qtenginio")
        if cross_building(self):
            args.append(f"-extprefix {self.package_folder}")
        if self._is_rdk_kirkstone:
            # Mirror setup_and_build_macos_kirkstone_qt563.sh: point -hostprefix at
            # a SEPARATE (build-local) staging dir and pass -nomake tools.
            #
            # -hostprefix is the decisive flag for cross builds. Without it Qt's
            # configure sets HAVE_HOST_PATH=false, which makes QT_REL_HOST_DATA
            # collapse onto QT_REL_INSTALL_ARCHDATA so QT_HOST_DATA points at the
            # (empty, install) prefix. That prevents qt_build_config.prf from
            # setting CONFIG += prefix_build, so inter-module links (e.g. Widgets
            # -> Core) resolve libQt5Core.so via the yet-unpopulated package/lib
            # path and fail. A distinct -hostprefix keeps QT_HOST_DATA off the
            # install prefix, so prefix_build is enabled and module deps resolve
            # to the build tree (<build>/qtbase/lib) during the build.
            host_prefix = os.path.join(self.build_folder, "qt_host")
            args.append(f"-hostprefix {host_prefix}")
            args.append("-nomake tools")
        args.append("-v")
        if self.options.commercial:
            args.append("-commercial")
        else:
            args.append("-opensource")
        if not self.options.gui:
            args.append("-no-gui")
        if not self.options.widgets:
            args.append("-no-widgets")
        if not self.options.shared:
            args.insert(0, "-static")
            if is_msvc(self) and "MT" in msvc_runtime_flag(self):
                args.append("-static-runtime")
        else:
            args.insert(0, "-shared")
        if self.options.multiconfiguration:
            args.append("-debug-and-release")
        elif self.settings.build_type == "Debug":
            args.append("-debug")
        elif self.settings.build_type == "Release":
            args.append("-release")
        elif self.settings.build_type == "RelWithDebInfo":
            args.append("-release")
            args.append("-force-debug-info")
        elif self.settings.build_type == "MinSizeRel":
            args.append("-release")
            args.append("-optimize-size")

        # Only skip modules that actually exist in the Qt source directory
        for module in self._submodules:
            if module in self.options and not self.options.get_safe(module):
                # Check if the module directory actually exists in the source
                module_path = os.path.join(self.source_folder, "qt5", module)
                self.output.info(
                    f"Checking module {module}: path={module_path}, exists={os.path.isdir(module_path)}"
                )
                if os.path.isdir(module_path):
                    args.append("-skip " + module)
                else:
                    self.output.warning(
                        f"Skipping non-existent module {module} - not adding to configure args"
                    )

        # RDK Kirkstone: qtwayland is cross-built in a dedicated pass after the
        # main make (see _rdk_build_qtwayland), mirroring the wayland step of
        # setup_and_build_macos_kirkstone_qt563.sh. Building it inline links
        # WaylandClient against the sysroot Qt 5.15 libQt5Gui (Qt_5_PRIVATE_API
        # mismatch), so skip it here and build it separately against the freshly
        # built Qt 5.6.3 libs.
        if self._is_rdk_kirkstone and self.options.get_safe("qtwayland"):
            args.append("-skip qtwayland")

        args.append("--zlib=system")

        # openGL
        opengl = self.options.get_safe("opengl", "no")
        if opengl == "no":
            args += ["-no-opengl"]
        elif opengl == "es2":
            args += ["-opengl es2"]
        elif opengl == "desktop":
            args += ["-opengl desktop"]
        elif opengl == "dynamic":
            args += ["-opengl dynamic"]

        # Linux windowing: the core-app Qt 5.6.3 SDK is built headless and renders
        # through the offscreengl/OSMesa platform plugin, so xcb/X11 is not built.
        # Match the from-source setup_and_build_linux_x86_qt563.sh, which passes
        # -no-xcb, and make the outcome deterministic instead of relying on Qt's
        # xcb auto-detection (which depends on X11 dev headers being absent).
        if self.settings.os in ["Linux", "FreeBSD"] and not self.options.get_safe("with_x11", False):
            args += ["-no-xcb"]

        # openSSL: the openssl option is removed for 5.6.3. Apple platforms get a
        # working TLS stack from SecureTransport (see package_info), but Linux and
        # FreeBSD have no native backend, so Qt must be linked against OpenSSL to
        # produce a usable QtNetwork SSL API (QSslSocket/QSslConfiguration/
        # QSslCertificate). Building with -no-openssl there compiles those classes
        # out and breaks consumers. This mirrors setup_and_build_linux_x86_qt563.sh,
        # which configures Qt with -openssl-linked. Other platforms keep SSL off.
        if self.settings.os in ["Linux", "FreeBSD"]:
            args += ["-openssl-linked"]
        else:
            args += ["-no-openssl"]

        # args.append("--iconv=" + ("gnu" if self.options.with_libiconv else "no"))# QTBUG-84708

        args.append("--glib=" + ("yes" if self.options.with_glib else "no"))
        args.append("--pcre=" + ("system" if self.options.get_safe("with_pcre2", False) else "qt"))
        args.append("--fontconfig=" + ("yes" if self.options.get_safe("with_fontconfig", False) else "no"))
        args.append("--icu=" + ("yes" if self.options.get_safe("with_icu", False) else "no"))
        args.append("--sql-mysql=" + ("yes" if self.options.get_safe("with_mysql", False) else "no"))

        args.append("--sql-psql=" + ("yes" if self.options.get_safe("with_pq", False) else "no"))
        args.append("--sql-odbc=" + ("yes" if self.options.get_safe("with_odbc", False) else "no"))
        # Explicitly disable other SQL drivers to avoid configure tests failures
        args.append("-no-sql-ibase")  # Firebird/InterBase
        args.append("-no-sql-db2")  # IBM DB2
        args.append("-no-sql-oci")  # Oracle
        args.append("-no-sql-tds")  # Sybase/MS SQL Server

        if self.options.qtmultimedia:
            args.append("--alsa=" + ("yes" if self.options.get_safe("with_libalsa", False) else "no"))
            args.append("--gstreamer" if self.options.get_safe("with_gstreamer", False) else "--no-gstreamer")
            args.append("--pulseaudio" if self.options.get_safe("with_pulseaudio", False) else "--no-pulseaudio")

        if self.options.with_dbus:
            args.append("-dbus-linked")
        elif is_apple_os(self) and not cross_building(self):
            # Match core-app local build: let Qt auto-detect D-Bus (runtime-loaded
            # libdbus) so the QtDBus module is produced, exactly like the reference
            # which passes no -dbus flag. Embedded/cross builds keep -no-dbus below.
            pass
        else:
            args.append("-no-dbus")

        opt_list = [
            ("with_freetype", "freetype"),
            ("with_harfbuzz", "harfbuzz"),
            ("with_libjpeg", "libjpeg"),
            ("with_libpng", "libpng"),
        ]

        for opt, conf_arg in opt_list:
            if self.options.get_safe(opt, False):
                if self.options.multiconfiguration:
                    args += ["-qt-" + conf_arg]
                else:
                    args += ["-system-" + conf_arg]
            elif conf_arg in ("freetype", "harfbuzz", "libjpeg", "libpng"):
                # Qt 5.6.3 deletes these options; use Qt's bundled copies for both
                # desktop and embedded builds. Matches core-app setup_and_build,
                # which passes -qt-libpng/-qt-libjpeg and lets freetype/harfbuzz
                # default to the bundled versions. Required for image decoding
                # (PNG/JPEG) and text shaping (HarfBuzz).
                args += ["-qt-" + conf_arg]
            else:
                args += ["-no-" + conf_arg]

        for dependency in self.dependencies.direct_host.values():
            args += [f"-I \"{s}\"" for s in dependency.cpp_info.aggregated_components().includedirs]
            args += [f"-D {s}" for s in dependency.cpp_info.aggregated_components().defines]

        if self.settings.os == "Macos":
            args += ["-no-framework"]
        elif self.settings.os == "Android":
            args += [f"-android-ndk-platform android-{self.settings.os.api_level}"]
            args += [f"-android-abis {android_abi(self)}"]

        if self.settings.get_safe("compiler.libcxx") == "libstdc++":
            args += ["-D_GLIBCXX_USE_CXX11_ABI=0"]
        elif self.settings.get_safe("compiler.libcxx") == "libstdc++11":
            args += ["-D_GLIBCXX_USE_CXX11_ABI=1"]

        if self.options.get_safe("android_sdk", ""):
            args += [f"-android-sdk {self.options.android_sdk}"]
        if self.options.sysroot:
            args += [f"-sysroot {self.options.sysroot}"]
        elif self._is_rdk_kirkstone:
            # The target sysroot is provided by the profile (tools.build:sysroot),
            # not the recipe's sysroot option. Qt cross-compilation requires it on
            # the configure line so qmake resolves the RDK headers/libraries.
            rdk_sysroot = self.conf.get("tools.build:sysroot", check_type=str)
            if rdk_sysroot:
                args += [f"-sysroot {rdk_sysroot}"]

        if self.options.device:
            args += [f"-device {self.options.device}"]
        else:
            xplatform_val = self._xplatform()
            if xplatform_val:
                if not cross_building(self, skip_x64_x86=True):
                    args += [f"-platform {xplatform_val}"]
                else:
                    # On a Linux build host, pin the host bootstrap tools
                    # (moc/uic/rcc) to the native linux-g++ spec so they never
                    # inherit the cross target toolchain, while the target is
                    # built with the retargeted arm-rdk mkspec.
                    if self._is_rdk_kirkstone and self._settings_build.os == "Linux":
                        args += ["-platform linux-g++"]
                    args += [f"-xplatform {xplatform_val}"]
            else:
                self.output.warn("host not supported: %s %s %s %s" %
                                 (self.settings.os, self.settings.compiler,
                                  self.settings.compiler.version, self.settings.arch))
        if self.options.cross_compile:
            args += [f"-device-option CROSS_COMPILE={self.options.cross_compile}"]
        elif self._is_rdk_kirkstone:
            args += [f"-device-option CROSS_COMPILE={self._rdk_cross_prefix}"]

        def _getenvpath(var):
            val = os.getenv(var)
            if val and self._settings_build.os == "Windows":
                val = val.replace("\\", "/")
                os.environ[var] = val
            return val

        # Skip on RDK: setting QMAKE_CC/QMAKE_CXX on the configure line applies
        # them globally and clobbers Qt's host bootstrap compiler. The RDK target
        # compiler comes from the target mkspec's CROSS_COMPILE prefix instead.
        if not is_msvc(self) and not self._is_rdk_kirkstone:
            value = _getenvpath("CC")
            if value:
                args += ['QMAKE_CC="' + value + '"',
                         'QMAKE_LINK_C="' + value + '"',
                         'QMAKE_LINK_C_SHLIB="' + value + '"']

            value = _getenvpath('CXX')
            if value:
                args += ['QMAKE_CXX="' + value + '"',
                         'QMAKE_LINK="' + value + '"',
                         'QMAKE_LINK_SHLIB="' + value + '"']

        # Unlike Qt 5.15+, Qt 5.6.3's configure does not accept qmake-style variable
        # assignments (e.g. QMAKE_CXXFLAGS+=...) on the command line: its argument
        # parser rejects any non-option token with "unknown argument". Collect the
        # extra compiler/linker flags here and inject them into the platform mkspec's
        # qmake.conf before configuring, which is the mechanism Qt 5.6.3 supports.
        extra_cflags = []
        extra_cxxflags = []
        extra_ldflags = []

        if self._settings_build.os == "Linux" and self.settings.compiler == "clang":
            extra_cxxflags.append("-ftemplate-depth=1024")

        if self.settings.compiler == "apple-clang" and self.options.qtmultimedia:
            # XCode 14.3 finally removes std::unary_function, so compilation fails
            # when using newer SDKs when using C++17 or higher.
            # This macro re-enables them. Should be safe to pass this macro even
            # in earlier versions, as it would have no effect.
            extra_cxxflags.append("-D_LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION=1")

        if self.options.qtwebengine and self.settings.os in ["Linux", "FreeBSD"]:
            args += ["-qt-webengine-ffmpeg",
                     "-system-webengine-opus",
                     "-webengine-jumbo-build 0"]

        if self.options.config:
            args.append(str(self.options.config))

        cxxflags = self.conf.get("tools.build:cxxflags", check_type=list)
        if cxxflags:
            extra_cxxflags += cxxflags

        # C sources (e.g. bundled freetype) need the same ARM march/float-ABI
        # flags; without them gnu/stubs-32.h selects the soft-float stubs header
        # that the armv7hf sysroot does not ship.
        cflags = self.conf.get("tools.build:cflags", check_type=list)
        if cflags:
            extra_cflags += cflags

        ldflags = self.conf.get("tools.build:sharedlinkflags", check_type=list)
        if ldflags:
            extra_ldflags += ldflags

        if extra_cflags or extra_cxxflags or extra_ldflags:
            xplatform_val = None if self.options.device else self._xplatform()
            if xplatform_val:
                qmake_conf = os.path.join(self.source_folder, "qt5", "qtbase",
                                          "mkspecs", xplatform_val, "qmake.conf")
                injected = ["",
                            "# Injected by Conan recipe: Qt 5.6.3 configure rejects "
                            "QMAKE_*+= assignments on the command line."]
                if extra_cflags:
                    injected.append("QMAKE_CFLAGS += %s" % " ".join(extra_cflags))
                if extra_cxxflags:
                    injected.append("QMAKE_CXXFLAGS += %s" % " ".join(extra_cxxflags))
                if extra_ldflags:
                    injected.append("QMAKE_LFLAGS += %s" % " ".join(extra_ldflags))
                with open(qmake_conf, "a", encoding="utf-8") as conf_file:
                    conf_file.write("\n".join(injected) + "\n")
            else:
                self.output.warn(
                    "Cannot inject extra compiler/linker flags into a mkspec: "
                    "unknown xplatform for %s/%s" % (self.settings.os, self.settings.compiler))

        if self._is_rdk_kirkstone and not self.options.device:
            xplatform_val = self._xplatform()
            if xplatform_val:
                rdk_qmake_conf = os.path.join(self.source_folder, "qt5", "qtbase",
                                              "mkspecs", xplatform_val, "qmake.conf")
                # Retarget the generic arm-gnueabi mkspec at the RDK cross prefix
                # (arm-rdk-linux-gnueabi-), then add the two tweaks the local_sdk
                # build applies to its linux-rdk-armv7-g++ spec: declare the ARM
                # target arch so Qt compiles the NEON/ARM source files, and clear
                # QMAKE_LFLAGS_NOUNDEF so private-class symbols with hidden
                # visibility link. Mirrors setup_and_build_macos_kirkstone_qt563.sh.
                replace_in_file(self, rdk_qmake_conf, "arm-linux-gnueabi-",
                                self._rdk_cross_prefix, strict=False)
                with open(rdk_qmake_conf, "a", encoding="utf-8") as conf_file:
                    # Blank QMAKE_CFLAGS_ISYSTEM (same as OpenEmbedded meta-qt5): the
                    # RDK toolchain keeps its libstdc++ headers under the target
                    # sysroot's usr/include/c++, so Qt's default -isystem for
                    # sysroot dep includes reorders usr/include ahead of the C++
                    # dir and breaks <cstdlib>'s "#include_next <stdlib.h>". Using
                    # plain -I preserves the built-in system search order.
                    conf_file.write("\nQMAKE_TARGET.arch = arm\nQMAKE_LFLAGS_NOUNDEF =\nQMAKE_CFLAGS_ISYSTEM =\n")

        os.mkdir("build_folder")
        with chdir(self, "build_folder"):
            if self._settings_build.os == "Macos":
                save(self, ".qmake.stash" , "")
                save(self, ".qmake.super" , "")

            self.run("%s %s" % (os.path.join(self.source_folder, "qt5", "configure"), " ".join(args)))

            if self._is_rdk_kirkstone:
                self._rdk_staged_make()
            else:
                self.run(self._make_program())

    def _rdk_staged_make(self):
        # Qt's cross prefix build on Linux resolves inter-module libraries via the
        # install prefix ($$[QT_INSTALL_LIBS] = <package>/lib/libQt5X.so), not the
        # build tree, yet those libs are not installed until package(). Reproduce
        # the phased build of setup_and_build_widget_linux_qt563.sh: populate
        # <package>/lib with symlinks to every built Qt lib between make passes so
        # links resolve, then drop the symlinks so package() installs real libs.
        make = self._make_program()
        build_root = os.path.join(self.build_folder, "build_folder")
        qtbase_lib = os.path.join(build_root, "qtbase", "lib")
        package_lib = os.path.join(self.package_folder, "lib")

        def _clear_package_lib():
            if os.path.islink(package_lib):
                os.unlink(package_lib)
            elif os.path.isdir(package_lib):
                shutil.rmtree(package_lib)

        def _aggregate():
            os.makedirs(package_lib, exist_ok=True)
            for so in glob.glob(os.path.join(build_root, "**", "libQt5*.so*"), recursive=True):
                dest = os.path.join(package_lib, os.path.basename(so))
                if not os.path.lexists(dest):
                    os.symlink(so, dest)
            # Qt 5.15 sysroot .prl files reference libQt5QmlModels, which does not
            # exist in Qt 5.6.3 (its content is part of libQt5Qml). Provide a
            # compat symlink so qtdeclarative/qmltest links against it.
            qml = os.path.join(package_lib, "libQt5Qml.so.5.6.3")
            if os.path.exists(qml):
                for name in ("libQt5QmlModels.so", "libQt5QmlModels.so.5.6.3",
                             "libQt5QmlModels.so.5.6", "libQt5QmlModels.so.5"):
                    dest = os.path.join(package_lib, name)
                    if not os.path.lexists(dest):
                        os.symlink(qml, dest)

        def _make(target="", keep_going=False):
            cmd = make
            if target:
                cmd += " " + target
            if keep_going:
                cmd += " -k"
            try:
                self.run(cmd)
            except ConanException:
                # -k passes tolerate host-only subtargets (qmldevtools, qdoc, ...)
                # that Qt 5.6.3 cannot cross-compile; required libs are verified
                # afterwards.
                if not keep_going:
                    raise

        # Phase 1: build qtbase with <package>/lib pointing at the qtbase build
        # lib so intra-qtbase links (Widgets -> Core, ...) resolve, then convert
        # <package>/lib to a real directory.
        os.makedirs(qtbase_lib, exist_ok=True)
        os.makedirs(self.package_folder, exist_ok=True)
        _clear_package_lib()
        os.symlink(qtbase_lib, package_lib)
        _make("module-qtbase")
        os.unlink(package_lib)
        _aggregate()

        # Phase 2: build the remaining modules. Cross-repo links (qtdeclarative ->
        # qtbase, Qml/QmlModels) fail until every module lib is visible, so keep
        # going and re-aggregate between passes.
        _make(keep_going=True)
        _aggregate()
        _make(keep_going=True)
        _aggregate()

        # qtwayland is -skip'd from the main configure; cross-build it in a
        # dedicated pass (mirrors setup_and_build_macos_kirkstone_qt563.sh) so
        # WaylandClient links the built Qt 5.6.3 libs, then aggregate its libs.
        if self.options.get_safe("qtwayland"):
            self._rdk_build_qtwayland(build_root)
            _aggregate()

        # Verify the modules this configuration needs actually built (the -k
        # passes tolerate unbuildable host-only subtargets).
        required = ["libQt5Core"]
        if self.options.gui:
            required.append("libQt5Gui")
        if self.options.widgets:
            required.append("libQt5Widgets")
        if self.options.get_safe("qtdeclarative"):
            required += ["libQt5Qml", "libQt5Quick"]
        if self.options.get_safe("qtwayland"):
            required.append("libQt5WaylandClient")
        # WebSockets and Svg ship in the widget and are linked by epg, so a
        # silent -k build failure of either must fail here, not surface later as
        # a consumer "Cannot obtain 'location'" error.
        if self.options.get_safe("qtwebsockets"):
            required.append("libQt5WebSockets")
        if self.options.get_safe("qtsvg"):
            required.append("libQt5Svg")
        missing = [lib for lib in required
                   if not glob.glob(os.path.join(build_root, "**", lib + ".so*"), recursive=True)]
        if missing:
            raise ConanException(
                "RDK Qt cross build did not produce required libraries: %s" % ", ".join(missing))

        # Drop the temporary symlinks so package() `make install` writes real libs.
        for link in glob.glob(os.path.join(package_lib, "*")):
            if os.path.islink(link):
                os.unlink(link)

    def _rdk_build_qtwayland(self, build_root):
        # Cross-build qtwayland separately, mirroring the wayland step of
        # setup_and_build_macos_kirkstone_qt563.sh. QMAKE_LIBDIR_QT points the
        # linker at the freshly built Qt 5.6.3 libs (build/qtbase/lib) so
        # WaylandClient is not linked against the sysroot Qt 5.15 libQt5Gui
        # (which carries mismatched Qt_5_PRIVATE_API symbol versions).
        make = self._make_program()
        host_qmake = os.path.join(build_root, "qtbase", "bin", "qmake")
        syncqt = os.path.join(self.source_folder, "qt5", "qtbase", "bin", "syncqt.pl")
        qtwayland_src = os.path.join(self.source_folder, "qt5", "qtwayland")
        qtbase_lib = os.path.join(build_root, "qtbase", "lib")
        wl_build = os.path.join(build_root, "qtwayland")
        # tool_requires("wayland") puts wayland-scanner on PATH only inside
        # self.run's build env, not this recipe process, so shutil.which misses
        # it; resolve the executable from the build-context dependency.
        scanner = shutil.which("wayland-scanner")
        if not scanner:
            try:
                wl_dep = self.dependencies.build["wayland"]
                for _bindir in wl_dep.cpp_info.bindirs:
                    _cand = os.path.join(_bindir, "wayland-scanner")
                    if os.path.isfile(_cand):
                        scanner = _cand
                        break
            except Exception:
                pass

        if not os.path.isfile(host_qmake):
            raise ConanException(f"qtwayland build: host qmake not found at {host_qmake}")
        if not os.path.isdir(qtwayland_src):
            raise ConanException(f"qtwayland build: source not found at {qtwayland_src}")
        if not scanner:
            raise ConanException("qtwayland build: wayland-scanner not found "
                                 "(tool_requires wayland provides it).")

        os.makedirs(wl_build, exist_ok=True)
        with chdir(self, wl_build):
            self.run(f'"{host_qmake}" "{os.path.join(qtwayland_src, "qtwayland.pro")}" '
                     f'"QMAKE_WAYLAND_SCANNER={scanner}" "QMAKE_LIBDIR_QT={qtbase_lib}"')
            # syncqt generates the flat QtWaylandClient forwarding headers
            # (qtwaylandclientglobal.h, ...) the Sky plugins compile against.
            if os.path.isfile(syncqt):
                self.run(f'perl "{syncqt}" -version {self.version} -module QtWaylandClient '
                         f'-outdir "{wl_build}" "{qtwayland_src}"', ignore_errors=True)
            # Recurse to emit the sub-Makefiles, then build the client lib and
            # plugins with targeted makes. src/client is fatal (it produces
            # libQt5WaylandClient, verified below); plugins are best-effort.
            self.run(f"{make} sub-src -k", ignore_errors=True)
            self.run(f'{make} -C "{os.path.join(wl_build, "src", "client")}"')
            self.run(f'{make} -C "{os.path.join(wl_build, "src", "plugins", "platforms")}"',
                     ignore_errors=True)
            for _egl in (os.path.join(wl_build, "src", "hardwareintegration", "client", "wayland-egl"),
                         os.path.join(wl_build, "src", "plugins", "hardwareintegration", "client", "wayland-egl")):
                if os.path.isdir(_egl):
                    self.run(f'{make} -C "{_egl}"', ignore_errors=True)
                    break

    @property
    def _cmake_core_extras_file(self):
        return os.path.join("lib", "cmake", "Qt5Core", "conan_qt_core_extras.cmake")

    def _cmake_qt5_private_file(self, module):
        return os.path.join("lib", "cmake", f"Qt5{module}", f"conan_qt_qt5_{module.lower()}private.cmake")

    @property
    def _event_dispatcher_reqs(self):
        reqs = ["Core", "Gui"]
        if self.options.with_glib:
            reqs.append("glib::glib")

        return reqs

    def package(self):
        with chdir(self, "build_folder"):
            if self._is_rdk_kirkstone:
                # -k: tolerate host-only subtargets (qmldevtools, qdoc, ...) that
                # Qt 5.6.3 cannot cross-compile; the required module libs were
                # verified in build().
                self.run(f"{self._make_program()} install -k", ignore_errors=True)
            else:
                self.run(f"{self._make_program()} install")
        if self._is_rdk_kirkstone and self.options.get_safe("qtwayland"):
            # qtwayland was -skip'd from the main build and cross-built separately
            # (see _rdk_build_qtwayland), so the main `make install` doesn't know
            # about it. Install the built client lib + plugins into the package.
            wl_build = os.path.join(self.build_folder, "build_folder", "qtwayland")
            for _sub in (os.path.join("src", "client"),
                         os.path.join("src", "plugins", "platforms"),
                         os.path.join("src", "hardwareintegration", "client", "wayland-egl"),
                         os.path.join("src", "plugins", "hardwareintegration", "client", "wayland-egl")):
                _d = os.path.join(wl_build, _sub)
                if os.path.isdir(_d):
                    self.run(f'{self._make_program()} -C "{_d}" install', ignore_errors=True)
        if self._is_rdk_kirkstone:
            # make install -k can skip a module's install subtarget (e.g.
            # qtwayland) while its libs were built. Backfill any built module
            # libs the install missed so the package matches the components
            # package_info() declares (Qt5WaylandClient, ...) and CMakeDeps can
            # resolve their location.
            build_root = os.path.join(self.build_folder, "build_folder")
            package_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(package_lib, exist_ok=True)
            for _so in glob.glob(os.path.join(build_root, "**", "libQt5*.so*"), recursive=True):
                _dest = os.path.join(package_lib, os.path.basename(_so))
                if os.path.lexists(_dest):
                    continue
                if os.path.islink(_so):
                    os.symlink(os.readlink(_so), _dest)
                else:
                    shutil.copy2(_so, _dest)
        if self._is_rdk_kirkstone:
            # Conan's CMakeConfigDeps deduces a shared lib's on-disk location from
            # the bare `lib<name>.so` dev symlink. `make install -k` and the
            # backfill above can leave a module with only its versioned files
            # (libQt5X.so.5.6.3) on some build hosts, which makes deduce_location
            # fail with "Cannot obtain 'location'". Normalize the SONAME chain so
            # every packaged Qt5 lib exposes .so / .so.5 / .so.5.6 -> .so.5.6.3.
            package_lib = os.path.join(self.package_folder, "lib")
            v = Version(self.version)
            _full = f".so.{self.version}"
            for _real in glob.glob(os.path.join(package_lib, f"libQt5*{_full}")):
                if os.path.islink(_real):
                    continue
                _stem = os.path.basename(_real)[:-len(_full)] + ".so"
                for _suffix in ("", f".{v.major}", f".{v.major}.{v.minor}"):
                    _dest = os.path.join(package_lib, _stem + _suffix)
                    if os.path.lexists(_dest):
                        if os.path.islink(_dest) and not os.path.exists(_dest):
                            os.unlink(_dest)  # replace a dangling symlink
                        else:
                            continue
                    os.symlink(os.path.basename(_real), _dest)
        if self._is_rdk_kirkstone:
            # -hostprefix diverts host data (mkspecs) to the host prefix, so
            # make install leaves <package>/mkspecs empty; package_info()
            # asserts it exists. Copy the installed host mkspecs (falling back
            # to the build/source trees) into the package.
            pkg_mkspecs = os.path.join(self.package_folder, "mkspecs")
            if not os.path.isdir(pkg_mkspecs):
                host_prefix = os.path.join(self.build_folder, "qt_host")
                for _src in (os.path.join(host_prefix, "mkspecs"),
                             os.path.join(self.build_folder, "build_folder", "qtbase", "mkspecs"),
                             os.path.join(self.source_folder, "qt5", "qtbase", "mkspecs")):
                    if os.path.isdir(_src):
                        shutil.copytree(_src, pkg_mkspecs, symlinks=True)
                        break
        if self._is_rdk_kirkstone:
            # -hostprefix diverts the host tools (qmake, moc, rcc, uic,
            # qmlimportscanner, ...) to the host prefix, so <package>/bin lacks
            # them. Consumers run these host-native tools at build time
            # (AUTOMOC/AUTORCC/AUTOUIC and the imported Qt5::* executables), so
            # copy them into the package bin dir.
            host_bin = os.path.join(self.build_folder, "qt_host", "bin")
            pkg_bin = os.path.join(self.package_folder, "bin")
            if os.path.isdir(host_bin):
                os.makedirs(pkg_bin, exist_ok=True)
                for _f in os.listdir(host_bin):
                    _src = os.path.join(host_bin, _f)
                    _dst = os.path.join(pkg_bin, _f)
                    if os.path.lexists(_dst):
                        continue
                    if os.path.islink(_src):
                        os.symlink(os.readlink(_src), _dst)
                    elif os.path.isfile(_src):
                        shutil.copy2(_src, _dst)
        if self._is_rdk_kirkstone:
            # Qt 5.15 sysroot .prl files reference libQt5QmlModels, absent in Qt
            # 5.6.3 (folded into libQt5Qml). Recreate the compat symlinks in the
            # packaged lib dir so consumers linking QtQuick resolve them.
            package_lib = os.path.join(self.package_folder, "lib")
            qml = os.path.join(package_lib, "libQt5Qml.so.5.6.3")
            if os.path.exists(qml):
                for name in ("libQt5QmlModels.so", "libQt5QmlModels.so.5.6.3",
                             "libQt5QmlModels.so.5.6", "libQt5QmlModels.so.5"):
                    dest = os.path.join(package_lib, name)
                    if not os.path.lexists(dest):
                        os.symlink("libQt5Qml.so.5.6.3", dest)
        save(self, os.path.join(self.package_folder, "bin", "qt.conf"), """[Paths]
Prefix = ..""")
        # Apply the header polyfills used by core-app setup_and_build
        # (qt563_install.patch) so the packaged headers match local_sdk and
        # can build epg / modern C++ consumers. Same invocation as the
        # scripts: patch -p1 --forward --ignore-whitespace at the prefix.
        install_patch = os.path.join(self.recipe_folder, "qt563_install.patch")
        self.run(f'patch -p1 --batch --forward --ignore-whitespace -d "{self.package_folder}" < "{install_patch}" || true')
        # qpa is a symlinked dir (not represented in the patch); recreate it.
        qpa_targets = glob.glob(os.path.join(self.package_folder, "include", "QtGui", "*", "QtGui", "qpa"))
        if qpa_targets:
            for link in [os.path.join(self.package_folder, "include", "qpa"),
                         os.path.join(self.package_folder, "include", "QtGui", "qpa")]:
                if not os.path.lexists(link):
                    os.symlink(qpa_targets[0], link)
        # Linux: build and package the OSMesa-based offscreen GL platform plugin
        # (QT_QPA_PLATFORM=offscreengl) so component tests run headless without
        # X11/EGL. Mirrors setup_and_build_linux_x86_qt563.sh: compile the
        # vendored plugin with the packaged qmake; qt_plugin installs the .so
        # straight into <prefix>/plugins/platforms. OSMesa is dlopen'd at runtime
        # (libosmesa6), so there is no link-time dependency. Skipped for the RDK
        # Kirkstone cross target, which renders on-device via wayland-egl.
        if (self.settings.os == "Linux" and not self._is_rdk_kirkstone
                and self.options.gui and self.options.get_safe("opengl", "no") != "no"):
            osgl_src = os.path.join(self.recipe_folder, "addons", "offscreengl-src")
            osgl_build = os.path.join(self.build_folder, "offscreengl-build")
            rmdir(self, osgl_build)
            os.makedirs(osgl_build)
            qmake = os.path.join(self.package_folder, "bin", "qmake")
            with chdir(self, osgl_build):
                self.run(f'"{qmake}" "{os.path.join(osgl_src, "offscreengl.pro")}" QMAKE_CXXFLAGS+="-std=gnu++14"')
                self.run(self._make_program())
        # RDK Kirkstone ARMv7: cross-compile the NEON/libproxy stubs and the
        # Sky wayland shell/input plugins into the package, reproducing the
        # neon-lib, libproxy and wayland steps of the local_sdk build.
        if self._is_rdk_kirkstone:
            self._package_rdk_kirkstone_extras()
        copy(self, "*LICENSE*", os.path.join(self.source_folder, "qt5/"), os.path.join(self.package_folder, "licenses"),
             excludes="qtbase/examples/*")
        for module in self._submodules:
            if not self.options.get_safe(module):
                rmdir(self, os.path.join(self.package_folder, "licenses", module))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # For the 5.6.3 SDK/drop-in use case, core-app consumes Qt via a raw
        # find_package(Qt5 ...) against lib/cmake (not Conan CMakeDeps), so the
        # qmake-generated Qt5*Config.cmake files must be retained. CMakeDeps
        # consumers ignore the in-package configs (they use the generated ones
        # under the build folder), so keeping them is safe and makes the package
        # drop-in ready without manual supplementation from the build tree.
        cmake_strip_masks = ["Find*.cmake"]
        for mask in cmake_strip_masks:
            rm(self, mask, self.package_folder, recursive=True)
        rm(self, "*.la*", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.pdb*", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True)
        rm(self, "*.pdb", os.path.join(self.package_folder, "plugins"), recursive=True)
        # "Qt5Bootstrap" is internal Qt library - removing it to avoid linking error, since it contains
        # symbols that are also in "Qt5Core.lib". It looks like there is no "Qt5Bootstrap.dll".
        for fl in glob.glob(os.path.join(self.package_folder, "lib", "*Qt5Bootstrap*")):
            os.remove(fl)

        # Keep every qmake cmake module dir for the 5.6.3 SDK drop-in (Network,
        # Sql, Test, WebSockets, Xml, ... have no <module>Macros.cmake and would
        # otherwise be removed, breaking raw find_package(Qt5 COMPONENTS ...)).

        extension = ""
        if self._settings_build.os == "Windows":
            extension = ".exe"
        v = Version(self.version)
        filecontents = textwrap.dedent(f"""\
            set(QT_CMAKE_EXPORT_NAMESPACE Qt5)
            set(QT_VERSION_MAJOR {v.major})
            set(QT_VERSION_MINOR {v.minor})
            set(QT_VERSION_PATCH {v.patch})
        """)
        targets = {}
        targets["Core"] = ["moc", "rcc", "qmake"]
        targets["DBus"] = ["qdbuscpp2xml", "qdbusxml2cpp"]
        if self.options.widgets:
            targets["Widgets"] = ["uic"]
        if self.options.qttools:
            targets["Tools"] = ["qhelpgenerator", "qcollectiongenerator", "qdoc", "qtattributionsscanner"]
            targets[""] = ["lconvert", "lrelease", "lupdate"]
        if self.options.qtremoteobjects:
            targets["RemoteObjects"] = ["repc"]
        if self.options.qtscxml:
            targets["Scxml"] = ["qscxmlc"]
        for namespace, targets in targets.items():
            for target in targets:
                filecontents += textwrap.dedent("""\
                    if(NOT TARGET ${{QT_CMAKE_EXPORT_NAMESPACE}}::{target})
                        add_executable(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} IMPORTED)
                        set_target_properties(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} PROPERTIES IMPORTED_LOCATION ${{CMAKE_CURRENT_LIST_DIR}}/../../../bin/{target}{ext})
                        set(Qt5{namespace}_{uppercase_target}_EXECUTABLE ${{QT_CMAKE_EXPORT_NAMESPACE}}::{target})
                    endif()
                    """.format(target=target, ext=extension, namespace=namespace, uppercase_target=target.upper()))

        if self.settings.os == "Windows":
            filecontents += textwrap.dedent("""\
                set(Qt5Core_QTMAIN_LIBRARIES Qt5::WinMain)
                if (NOT Qt5_NO_LINK_QTMAIN)
                    set(_isExe $<STREQUAL:$<TARGET_PROPERTY:TYPE>,EXECUTABLE>)
                    set(_isWin32 $<BOOL:$<TARGET_PROPERTY:WIN32_EXECUTABLE>>)
                    set(_isNotExcluded $<NOT:$<BOOL:$<TARGET_PROPERTY:Qt5_NO_LINK_QTMAIN>>>)
                    set(_isPolicyNEW $<TARGET_POLICY:CMP0020>)
                    set_property(TARGET Qt5::Core APPEND PROPERTY
                        INTERFACE_LINK_LIBRARIES
                            $<$<AND:${_isExe},${_isWin32},${_isNotExcluded},${_isPolicyNEW}>:Qt5::WinMain>
                    )
                    unset(_isExe)
                    unset(_isWin32)
                    unset(_isNotExcluded)
                    unset(_isPolicyNEW)
                endif()
                """)

        filecontents += textwrap.dedent(f"""\
            if(NOT DEFINED QT_DEFAULT_MAJOR_VERSION)
                set(QT_DEFAULT_MAJOR_VERSION {v.major})
            endif()
            """)
        filecontents += 'set(CMAKE_AUTOMOC_MACRO_NAMES "Q_OBJECT" "Q_GADGET" "Q_GADGET_EXPORT" "Q_NAMESPACE" "Q_NAMESPACE_EXPORT")\n'
        save(self, os.path.join(self.package_folder, self._cmake_core_extras_file), filecontents)

        def _create_private_module(module, dependencies=[]):
            if "Core" not in dependencies:
                dependencies.append("Core")
            if module not in dependencies:
                dependencies.append(module)

            dependencies_string = ';'.join(f'Qt5::{dependency}' for dependency in dependencies)
            contents = textwrap.dedent("""\
            if(NOT TARGET Qt5::{0}Private)
                add_library(Qt5::{0}Private INTERFACE IMPORTED)
                set_target_properties(Qt5::{0}Private PROPERTIES
                    INTERFACE_INCLUDE_DIRECTORIES "${{CMAKE_CURRENT_LIST_DIR}}/../../../include/Qt{0}/{1};${{CMAKE_CURRENT_LIST_DIR}}/../../../include/Qt{0}/{1}/Qt{0}"
                    INTERFACE_LINK_LIBRARIES "{2}"
                )

                add_library(Qt::{0}Private INTERFACE IMPORTED)
                set_target_properties(Qt::{0}Private PROPERTIES
                    INTERFACE_LINK_LIBRARIES "Qt5::{0}Private"
                    _qt_is_versionless_target "TRUE"
                )
            endif()""".format(module, self.version, dependencies_string))

            save(self, os.path.join(self.package_folder, self._cmake_qt5_private_file(module)), contents)

        _create_private_module("Core")

        if self.options.gui:
            _create_private_module("Gui", ["CorePrivate", "Gui"])
            _create_private_module("FontDatabaseSupport", ["Core", "Gui"])
            _create_private_module("EventDispatcherSupport", self._event_dispatcher_reqs)

        if self.options.widgets:
            _create_private_module("Widgets", ["CorePrivate", "Gui", "GuiPrivate"])

        if self.options.qtdeclarative:
            _create_private_module("Qml", ["CorePrivate", "Qml"])
            if self.options.gui:
                _create_private_module("Quick", ["CorePrivate", "GuiPrivate", "QmlPrivate", "Quick"])

        if self.options.qtscxml:
            _create_private_module("Scxml", ["Scxml", "Qml"])

    def _package_rdk_kirkstone_extras(self):
        # Cross-compile the ARM stubs and Sky wayland plugins that the local_sdk
        # build (setup_and_build_macos_kirkstone_qt563.sh) layers on top of the Qt
        # install so the packaged Qt is a drop-in replacement for the device.
        lib_dir = os.path.join(self.package_folder, "lib")
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cross_cc = execs.get("c")
        sysroot = self.conf.get("tools.build:sysroot", check_type=str)
        if not cross_cc or not sysroot:
            raise ConanException("RDK Kirkstone build requires tools.build:compiler_executables "
                                 "and tools.build:sysroot to be set by the profile.")
        arm_flags = "-march=armv7-a -mthumb -mfpu=neon -mfloat-abi=hard"
        stubs_dir = os.path.join(self.recipe_folder, "addons", "stubs")

        # --- neon-lib: libQt5GuiNeon.so stub -----------------------------------
        # libQt5Gui.so.5 built with NEON references ARMv8/NEON symbols the ARMv7
        # toolchain does not emit; this stub satisfies the dynamic linker (Qt's
        # runtime feature detection never calls them on non-NEON hardware).
        neon_lib = os.path.join(lib_dir, "libQt5GuiNeon.so")
        self.run(f'"{cross_cc}" -shared -fPIC {arm_flags} '
                 f'-o "{neon_lib}" "{os.path.join(stubs_dir, "neon_stub.c")}" '
                 f'--sysroot="{sysroot}"')

        # Add libQt5GuiNeon.so to libQt5Gui's DT_NEEDED so it is pulled in at
        # runtime. patchelf is optional; warn (do not fail) if unavailable, matching
        # the local_sdk build.
        gui_lib = None
        for cand in sorted(glob.glob(os.path.join(lib_dir, "libQt5Gui.so.5*"))):
            if os.path.isfile(cand) and not os.path.islink(cand):
                gui_lib = cand
                break
        if gui_lib and shutil.which("patchelf"):
            needed = StringIO()
            try:
                self.run(f'patchelf --print-needed "{gui_lib}"', needed)
            except ConanException:
                pass
            if "libQt5GuiNeon.so" not in needed.getvalue():
                self.run(f'patchelf --add-needed libQt5GuiNeon.so "{gui_lib}"')
        elif not shutil.which("patchelf"):
            self.output.warning("patchelf not found; libQt5Gui will not DT_NEED libQt5GuiNeon.so.")

        # --- libproxy: stub libproxy.so.1 --------------------------------------
        # libQt5Network links px_proxy_factory_* which is absent on RDK Kirkstone.
        libproxy = os.path.join(lib_dir, "libproxy.so.1")
        self.run(f'"{cross_cc}" -shared -fPIC {arm_flags} -Wl,-soname,libproxy.so.1 '
                 f'-o "{libproxy}" "{os.path.join(stubs_dir, "libproxy_stub.c")}" '
                 f'--sysroot="{sysroot}"')

        # --- libqt_wl_protocols.so ---------------------------------------------
        # The bundled wayland platform plugin dlopen's the wire-protocol symbols
        # generated by qtwayland (wayland-*-protocol.c under the qtwayland build).
        # Those generated sources only exist while Qt is built, so compile the
        # aggregate protocol library here (mirrors the local_sdk package-widget
        # step) instead of leaving it to the consumer.
        self._package_rdk_wl_protocols(lib_dir, cross_cc, sysroot, arm_flags)

        # --- qtwayland module .pri files ---------------------------------------
        # The Sky plugins' qmake (load(qt_plugin) + PLUGIN_TYPE=...) needs a module
        # that claims their plugin type via MODULE_PLUGIN_TYPES. That declaration
        # lives in mkspecs/modules/qt_lib_waylandclient.pri, generated by the
        # qtwayland build but not installed by the targeted `make -C src/... install`
        # above. Copy it (and its _private counterpart) into the package mkspecs so
        # qmake resolves QT += waylandclient-private and claims the plugin types.
        wl_mkspecs = os.path.join(self.build_folder, "build_folder", "qtwayland", "mkspecs")
        pkg_modules = os.path.join(self.package_folder, "mkspecs", "modules")
        os.makedirs(pkg_modules, exist_ok=True)
        for _pri in ("qt_lib_waylandclient.pri", "qt_lib_waylandclient_private.pri"):
            for _srcdir in (os.path.join(wl_mkspecs, "modules-inst"),
                            os.path.join(wl_mkspecs, "modules")):
                _src = os.path.join(_srcdir, _pri)
                if os.path.isfile(_src):
                    shutil.copy2(_src, os.path.join(pkg_modules, _pri))
                    break
        # Qt 5.6.3's qtwayland omits wayland-shell-integration from the
        # waylandclient module's plugin_types, so load(qt_plugin) rejects the
        # wl-simple-shell plugin ("No module claims plugin type"). Inject it,
        # mirroring the sed in setup_and_build_macos_kirkstone_qt563.sh.
        _client_pri = os.path.join(pkg_modules, "qt_lib_waylandclient.pri")
        if os.path.isfile(_client_pri):
            _content = load(self, _client_pri)
            if "wayland-shell-integration" not in _content:
                save(self, _client_pri, _content.replace(
                    "QT.waylandclient.plugin_types =",
                    "QT.waylandclient.plugin_types = wayland-shell-integration", 1))

        # --- Sky wayland shell / input-device integration plugins --------------
        self._build_rdk_wayland_plugin(
            name="wl-simple-shell",
            plugin_type="wayland-shell-integration",
            src_dir=os.path.join(self.recipe_folder, "addons", "wl-simple-shell-src"),
            protocols=[("simpleshell.xml", "simple-shell"), ("skyshell.xml", "skyq-shell")],
            pro_body=_WL_SIMPLE_SHELL_PRO,
        )
        self._build_rdk_wayland_plugin(
            name="skyq-input",
            plugin_type="wayland-inputdevice-integration",
            src_dir=os.path.join(self.recipe_folder, "addons", "skyq-input-src"),
            protocols=[("skyq-input.xml", "skyq-input")],
            pro_body=_SKYQ_INPUT_PRO,
        )

    def _package_rdk_wl_protocols(self, lib_dir, cross_cc, sysroot, arm_flags):
        # Cross-compile libqt_wl_protocols.so from the wayland wire-protocol
        # sources qtwayland generated during the build. Non-fatal: warn (do not
        # fail) if the generated sources are missing, matching the local_sdk build.
        client_dirs = glob.glob(
            os.path.join(self.build_folder, "**", "qtwayland", "**", "src", "client"),
            recursive=True)
        proto_srcs = []
        for d in client_dirs:
            proto_srcs = glob.glob(os.path.join(d, "wayland-*-protocol.c"))
            if proto_srcs:
                break
        if not proto_srcs:
            self.output.warning(
                "Skipping libqt_wl_protocols.so: no wayland-*-protocol.c sources "
                "found under the qtwayland build.")
            return
        out = os.path.join(lib_dir, "libqt_wl_protocols.so")
        quoted_srcs = " ".join(f'"{s}"' for s in proto_srcs)
        try:
            self.run(f'"{cross_cc}" --sysroot="{sysroot}" {arm_flags} '
                     f'-shared -fPIC -o "{out}" {quoted_srcs} -lwayland-client')
        except ConanException:
            self.output.warning("libqt_wl_protocols.so build failed; it will not be packaged.")

    def _build_rdk_wayland_plugin(self, name, plugin_type, src_dir, protocols, pro_body):        # Generate the wayland-scanner / qtwaylandscanner protocol glue and build
        # the plugin with the packaged (cross) qmake, then place the resulting ARM
        # .so under <prefix>/plugins/<plugin_type>/. Non-fatal on failure, matching
        # the local_sdk build which only warns for these plugins.
        qmake = os.path.join(self.package_folder, "bin", "qmake")
        qtws = os.path.join(self.package_folder, "bin", "qtwaylandscanner")
        if not os.path.isfile(qtws):
            # qtwaylandscanner is built by the qtwayland pass into the build tree
            # (not the -hostprefix). Try its known location first, then fall back
            # to a recursive search.
            _direct = os.path.join(self.build_folder, "build_folder", "qtwayland",
                                   "bin", "qtwaylandscanner")
            if os.path.isfile(_direct):
                qtws = _direct
            else:
                found = glob.glob(os.path.join(self.build_folder, "**", "qtwaylandscanner"), recursive=True)
                qtws = found[0] if found else qtws
        # tool_requires("wayland") is only on PATH inside self.run, not this recipe
        # process, so shutil.which misses wayland-scanner; resolve it from the
        # build-context dependency (mirrors _rdk_build_qtwayland).
        wscan = shutil.which("wayland-scanner")
        if not wscan:
            try:
                wl_dep = self.dependencies.build["wayland"]
                for _bindir in wl_dep.cpp_info.bindirs:
                    _cand = os.path.join(_bindir, "wayland-scanner")
                    if os.path.isfile(_cand):
                        wscan = _cand
                        break
            except Exception:
                pass
        if not (os.path.isfile(qmake) and wscan and os.path.isfile(qtws)):
            self.output.warning(
                f"Skipping {name} plugin: missing tool "
                f"(qmake={os.path.isfile(qmake)}, wayland-scanner={bool(wscan)}, "
                f"qtwaylandscanner={os.path.isfile(qtws)}).")
            return

        stage = os.path.join(self.build_folder, f"{name}-build")
        rmdir(self, stage)
        os.makedirs(stage)
        for pattern in ("*.cpp", "*.h", "*.json", "*.xml"):
            for f in glob.glob(os.path.join(src_dir, pattern)):
                shutil.copy(f, stage)
        save(self, os.path.join(stage, ".qmake.conf"),
             "load(qt_build_config)\nMODULE_VERSION = 5.6.3\n")
        save(self, os.path.join(stage, f"{name}.pro"), pro_body)

        try:
            with chdir(self, stage):
                for xml, base in protocols:
                    self.run(f'"{wscan}" client-header "{xml}" wayland-{base}-client-protocol.h')
                    self.run(f'"{wscan}" code "{xml}" wayland-{base}-protocol.c')
                    self.run(f'"{qtws}" client-header "{xml}" "" > qwayland-{base}.h')
                    self.run(f'"{qtws}" client-code "{xml}" "" > qwayland-{base}.cpp')
                # The standalone plugin build doesn't inherit the main build's
                # in-tree .qmake.cache, so the cross toolchain's --sysroot is not
                # applied and <cstddef> etc. resolve against the host /usr/include.
                # Pass the target sysroot explicitly (the in-tree build the .sh
                # does gets it from the device mkspec).
                qmake_cmd = f'"{qmake}" "{os.path.join(stage, name + ".pro")}"'
                rdk_sysroot = self.conf.get("tools.build:sysroot", check_type=str)
                if rdk_sysroot:
                    _sr = f"--sysroot={rdk_sysroot}"
                    qmake_cmd += (f' "QMAKE_CXXFLAGS+={_sr}" "QMAKE_CFLAGS+={_sr}" '
                                  f'"QMAKE_LFLAGS+={_sr}"')
                self.run(qmake_cmd)
                self.run(self._make_program())
        except ConanException:
            self.output.warning(f"{name} plugin build failed; it will not be packaged.")
            return

        dest_dir = os.path.join(self.package_folder, "plugins", plugin_type)
        so_name = f"lib{name}.so"
        dest = os.path.join(dest_dir, so_name)
        built = None
        candidates = [dest]
        candidates += glob.glob(os.path.join(stage, "**", so_name), recursive=True)
        candidates += glob.glob(os.path.join(self.package_folder, "plugins", "**", so_name), recursive=True)
        for cand in candidates:
            if os.path.isfile(cand):
                built = cand
                break
        if not built:
            self.output.warning(f"{name} plugin .so not found after build; not packaged.")
            return
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.abspath(built) != os.path.abspath(dest):
            shutil.copy(built, dest)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Qt5")
        self.cpp_info.set_property("pkg_config_name", "qt5")

        build_modules = {}

        def _add_build_module(component, module):
            if component not in build_modules:
                build_modules[component] = []
            build_modules[component].append(module)

        libsuffix = ""
        if self.settings.os == "Android":
            libsuffix = f"_{android_abi(self)}"
        if not self.options.multiconfiguration:
            if self.settings.build_type == "Debug":
                if self.settings.os == "Windows" and is_msvc(self):
                    libsuffix = "d"
                elif is_apple_os(self):
                    libsuffix = "_debug"

        def _get_corrected_reqs(requires):
            reqs = []
            for r in requires:
                if "::" in r:
                    corrected_req = r
                else:
                    corrected_req = f"qt{r}"
                    assert corrected_req in self.cpp_info.components, f"{corrected_req} required but not yet present in self.cpp_info.components"
                reqs.append(corrected_req)
            return reqs

        def _create_module(module, requires=[], has_include_dir=True):
            componentname = f"qt{module}"
            assert componentname not in self.cpp_info.components, f"Module {module} already present in self.cpp_info.components"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{module}")
            self.cpp_info.components[componentname].set_property("cmake_target_aliases", [f"Qt::{module}"])
            self.cpp_info.components[componentname].set_property("pkg_config_name", f"Qt5{module}")
            if module.endswith("Private"):
                libname = module[:-7]
            else:
                libname = module
            self.cpp_info.components[componentname].libs = [f"Qt5{libname}{libsuffix}"]
            if has_include_dir:
                self.cpp_info.components[componentname].includedirs = ["include", os.path.join("include", f"Qt{module}")]
            define = module.upper()
            if define == "TEST":
                define = "TESTLIB"
            elif define == "XCBQPA":
                define = "XCB_QPA_LIB"
            elif define.endswith("SUPPORT"):
                define = define.replace("SUPPORT", "_SUPPORT")
            self.cpp_info.components[componentname].defines = [f"QT_{define}_LIB"]
            if module != "Core" and "Core" not in requires:
                requires.append("Core")
            self.cpp_info.components[componentname].requires = _get_corrected_reqs(requires)

        def _create_plugin(pluginname, libname, plugintype, requires):
            componentname = f"qt{pluginname}"
            assert componentname not in self.cpp_info.components, f"Plugin {pluginname} already present in self.cpp_info.components"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{pluginname}")
            self.cpp_info.components[componentname].set_property("cmake_target_aliases", [f"Qt::{pluginname}"])
            self.cpp_info.components[componentname].libs = [libname + libsuffix]
            self.cpp_info.components[componentname].libdirs = [os.path.join("plugins", plugintype)]
            self.cpp_info.components[componentname].includedirs = []
            if "Core" not in requires:
                requires.append("Core")
            self.cpp_info.components[componentname].requires = _get_corrected_reqs(requires)

        core_reqs = ["zlib::zlib"]
        if self.options.get_safe("with_pcre2", False):
            core_reqs.append("pcre2::pcre2")
        if self.options.get_safe("with_doubleconversion", False):
            core_reqs.append("double-conversion::double-conversion")
        if self.options.get_safe("with_icu", False):
            core_reqs.append("icu::icu")
        if self.options.get_safe("with_zstd", False):
            core_reqs.append("zstd::zstd")
        if self.options.with_glib:
            core_reqs.append("glib::glib-2.0")

        _create_module("Core", core_reqs)
        if not self.options.shared and not self.options.get_safe("with_pcre2", False):
            # A static Qt configured with --pcre=qt links QtCore against the bundled
            # PCRE static lib (libqtpcre for Qt < 5.8, libqtpcre2 for newer). Expose
            # it so consumers of the static libs resolve the pcre16_*/pcre2_* symbols.
            # For a shared Qt the bundled PCRE is linked into libQt5Core directly and
            # no separate static lib is installed, so there is nothing to expose.
            bundled_pcre = "qtpcre"
            self.cpp_info.components["qtCore"].libs.append(f"{bundled_pcre}{libsuffix}")
        pkg_config_vars = [
            "host_bins=${prefix}/bin",
            "exec_prefix=${prefix}",
        ]
        self.cpp_info.components["qtCore"].set_property("pkg_config_custom_content", "\n".join(pkg_config_vars))

        if self.settings.build_type != "Debug":
            self.cpp_info.components['qtCore'].defines.append('QT_NO_DEBUG')

        if self.settings.os == "Windows":
            module = "WinMain"
            componentname = f"qt{module}"
            self.cpp_info.components[componentname].set_property("cmake_target_name", f"Qt5::{module}")
            self.cpp_info.components[componentname].set_property("cmake_target_aliases", [f"Qt::{module}"])
            self.cpp_info.components[componentname].libs = [f"qtmain{libsuffix}"]
            self.cpp_info.components[componentname].includedirs = []
            self.cpp_info.components[componentname].defines = []

        if self.options.with_dbus:
            _create_module("DBus", ["dbus::dbus"])
        if self.options.gui:
            gui_reqs = []
            if self.options.with_dbus:
                gui_reqs.append("DBus")
            if self.options.get_safe("with_freetype", False):
                gui_reqs.append("freetype::freetype")
            if self.options.get_safe("with_libpng", False):
                gui_reqs.append("libpng::libpng")
            if self.options.get_safe("with_fontconfig", False):
                gui_reqs.append("fontconfig::fontconfig")
            if self.settings.os in ["Linux", "FreeBSD"]:
                if self.options.qtwayland or self.options.get_safe("with_x11", False):
                    gui_reqs.append("xkbcommon::xkbcommon")
                if self.options.get_safe("with_x11", False):
                    gui_reqs.append("xorg::xorg")
            if self.options.get_safe("opengl", "no") != "no":
                gui_reqs.append("opengl::opengl")
            if self.options.get_safe("with_vulkan", False):
                gui_reqs.append("vulkan-loader::vulkan-loader")
                if is_apple_os(self):
                    gui_reqs.append("moltenvk::moltenvk")
            if self.options.get_safe("with_harfbuzz", False):
                gui_reqs.append("harfbuzz::harfbuzz")
            if self.options.get_safe("with_libjpeg", False) == "libjpeg-turbo":
                gui_reqs.append("libjpeg-turbo::libjpeg-turbo")
            if self.options.get_safe("with_libjpeg", False) == "libjpeg":
                gui_reqs.append("libjpeg::libjpeg")
            if self.options.get_safe("with_md4c", False):
                gui_reqs.append("md4c::md4c")
            _create_module("Gui", gui_reqs)
            _add_build_module("qtGui", self._cmake_qt5_private_file("Gui"))
            # Qt built with -opengl es2 (RDK Kirkstone) resolves glGenTextures/
            # glCreateShader/... against the device's GLESv2 lib, but Qt 5.6.3
            # omits -lGLESv2 from libQt5Gui.prl so it is not propagated. Add it as
            # a system lib, mirroring the .prl patch in setup_and_build_*_qt563.sh.
            if self.settings.os in ["Linux", "FreeBSD"] and self.options.get_safe("opengl") == "es2":
                self.cpp_info.components["qtGui"].system_libs.append("GLESv2")
            _create_plugin("QOffscreenIntegrationPlugin", "qoffscreen", "platforms", ["Core", "Gui"])

            # Qt 5.6.3 ships a single consolidated static libQt5PlatformSupport
            # instead of the fine-grained *Support libraries.
            _create_module("PlatformSupport", ["Core", "Gui"], has_include_dir=False)
            if is_apple_os(self):
                self.cpp_info.components["qtPlatformSupport"].frameworks.extend(["CoreFoundation", "CoreGraphics", "CoreText", "Foundation"])
                self.cpp_info.components["qtPlatformSupport"].frameworks.append("AppKit" if self.settings.os == "Macos" else "UIKit")
            if self.options.get_safe("with_fontconfig"):
                self.cpp_info.components["qtPlatformSupport"].requires.append("fontconfig::fontconfig")
            if self.options.get_safe("with_freetype"):
                self.cpp_info.components["qtPlatformSupport"].requires.append("freetype::freetype")

            if self.options.widgets:
                _create_module("Widgets", ["Gui"])
                _add_build_module("qtWidgets", self._cmake_qt5_private_file("Widgets"))
                if self.settings.os not in ["iOS", "watchOS", "tvOS"]:
                    _create_module("PrintSupport", ["Gui", "Widgets"])
                    if self.settings.os == "Macos" and not self.options.shared:
                        self.cpp_info.components["qtPrintSupport"].system_libs.append("cups")

            if self.settings.os in ["Android", "Emscripten"]:
                _create_module("EglSupport", ["Core", "Gui"])

            if self.settings.os == "Windows":
                windows_reqs = ["Core", "Gui"]
                windows_reqs.extend(["EventDispatcherSupport", "FontDatabaseSupport", "ThemeSupport", "AccessibilitySupport"])
                _create_module("WindowsUIAutomationSupport", ["Core", "Gui"])
                windows_reqs.append("WindowsUIAutomationSupport")
                if self.options.get_safe("with_vulkan"):
                    windows_reqs.append("VulkanSupport")
                _create_plugin("QWindowsIntegrationPlugin", "qwindows", "platforms", windows_reqs)
                _create_plugin("QWindowsVistaStylePlugin", "qwindowsvistastyle", "styles", windows_reqs)
                self.cpp_info.components["qtQWindowsIntegrationPlugin"].system_libs = ["advapi32", "dwmapi", "gdi32", "imm32",
                    "ole32", "oleaut32", "shell32", "shlwapi", "user32", "winmm", "winspool", "wtsapi32"]
            elif self.settings.os == "Android":
                android_reqs = ["Core", "Gui", "EventDispatcherSupport", "AccessibilitySupport", "FontDatabaseSupport", "EglSupport"]
                if self.options.get_safe("with_vulkan"):
                    android_reqs.append("VulkanSupport")
                _create_plugin("QAndroidIntegrationPlugin", "qtforandroid", "platforms", android_reqs)
                self.cpp_info.components["qtQAndroidIntegrationPlugin"].system_libs = ["android", "jnigraphics"]
            elif self.settings.os == "Macos":
                cocoa_reqs = ["Core", "Gui", "PlatformSupport"]
                if self.options.get_safe("with_vulkan"):
                    cocoa_reqs.append("VulkanSupport")
                if self.options.widgets:
                    cocoa_reqs.append("PrintSupport")
                _create_plugin("QCocoaIntegrationPlugin", "qcocoa", "platforms", cocoa_reqs)
                # In 5.6.3 QMacStyle is built into QtWidgets, so there is no
                # separate qmacstyle styles plugin.
                self.cpp_info.components["QCocoaIntegrationPlugin"].frameworks = ["AppKit", "Carbon", "CoreServices", "CoreVideo",
                    "IOKit", "IOSurface", "Metal", "QuartzCore"]
            elif self.settings.os in ["iOS", "tvOS"]:
                _create_plugin("QIOSIntegrationPlugin", "qios", "platforms", ["ClipboardSupport", "FontDatabaseSupport", "GraphicsSupport"])
                self.cpp_info.components["QIOSIntegrationPlugin"].frameworks = ["AudioToolbox", "Foundation", "Metal",
                    "MobileCoreServices", "OpenGLES", "QuartzCore", "UIKit"]
            elif self.settings.os == "watchOS":
                _create_plugin("QMinimalIntegrationPlugin", "qminimal", "platforms", ["EventDispatcherSupport", "FontDatabaseSupport"])
            elif self.settings.os == "Emscripten":
                _create_plugin("QWasmIntegrationPlugin", "qwasm", "platforms", ["Core", "Gui", "EventDispatcherSupport", "FontDatabaseSupport", "EglSupport"])
            elif self.settings.os in ["Linux", "FreeBSD"]:
                # Qt 5.6.3 consolidates all the fine-grained *Support libraries
                # (ServiceSupport, ThemeSupport, FontDatabaseSupport, EdidSupport,
                # XkbCommonSupport, AccessibilitySupport, ...) into a single
                # libQt5PlatformSupport, so the xcb QPA plugin depends on that
                # consolidated module instead of the per-feature ones.
                if self.options.get_safe("with_x11", False):
                    xcb_qpa_reqs = ["Core", "Gui", "PlatformSupport", "xorg::xorg"]
                    _create_module("XcbQpa", xcb_qpa_reqs, has_include_dir=False)
                    _create_plugin("QXcbIntegrationPlugin", "qxcb", "platforms", ["Core", "Gui", "XcbQpa"])
                    _create_plugin("QXcbGlxIntegrationPlugin", "qxcb-glx-integration", "xcbglintegrations", ["Core", "Gui"])

        if self.options.get_safe("with_sqlite3", False):
            _create_plugin("QSQLiteDriverPlugin", "qsqlite", "sqldrivers", ["sqlite3::sqlite3"])
        if self.options.get_safe("with_pq", False):
            _create_plugin("QPSQLDriverPlugin", "qsqlpsql", "sqldrivers", ["libpq::libpq"])
        if self.options.get_safe("with_mysql", False) == "mysql":
            _create_plugin("QMySQLDriverPlugin", "qsqlmysql", "sqldrivers", ["libmysqlclient::libmysqlclient"])
        if self.options.get_safe("with_mysql", False) == "mariadb":
            _create_plugin("QMySQLDriverPlugin", "qsqlmysql", "sqldrivers", ["mariadb-connector-c::mariadb-connector-c"])
        if self.options.get_safe("with_odbc", False):
            if self.settings.os != "Windows":
                _create_plugin("QODBCDriverPlugin", "qsqlodbc", "sqldrivers", ["odbc::odbc"])
        networkReqs = []
        if self.options.get_safe("openssl", False) or self.settings.os in ['Linux', 'FreeBSD']:
            networkReqs.append("openssl::openssl")
        if self.settings.os in ['Linux', 'FreeBSD'] and self.options.with_gssapi:
            networkReqs.append("krb5::krb5-gssapi")
        _create_module("Network", networkReqs)
        _create_module("Sql")
        _create_module("Test")
        if self.options.widgets and self.options.get_safe("opengl", "no") != "no":
            _create_module("OpenGLExtensions", ["Gui"])
        _create_module("Concurrent")
        _create_module("Xml")

        if self.options.qtdeclarative:
            _create_module("Qml", ["Network"])
            _add_build_module("qtQml", self._cmake_qt5_private_file("Qml"))
            self.cpp_info.components["qtQmlImportScanner"].set_property("cmake_target_name", "Qt5::QmlImportScanner")
            self.cpp_info.components["qtQmlImportScanner"].set_property("cmake_target_aliases", ["Qt::QmlImportScanner"])
            self.cpp_info.components["qtQmlImportScanner"].requires = _get_corrected_reqs(["Qml"])
            if self.options.gui:
                quick_reqs = ["Gui", "Qml"]
                _create_module("Quick", quick_reqs)
                _add_build_module("qtQuick", self._cmake_qt5_private_file("Quick"))
                if self.options.widgets:
                    _create_module("QuickWidgets", ["Gui", "Qml", "Quick", "Widgets"])
            _create_module("QuickTest", ["Test"])

        if self.options.qttools and self.options.gui and self.options.widgets:
            self.cpp_info.components["qtLinguistTools"].set_property("cmake_target_name", "Qt5::LinguistTools")
            self.cpp_info.components["qtLinguistTools"].set_property("cmake_target_aliases", ["Qt::LinguistTools"])
            _create_module("UiPlugin", ["Gui", "Widgets"])
            self.cpp_info.components["qtUiPlugin"].libs = [] # this is a collection of abstract classes, so this is header-only
            self.cpp_info.components["qtUiPlugin"].libdirs = []
            _create_module("UiTools", ["UiPlugin", "Gui", "Widgets"])
            if not cross_building(self):
                _create_module("Designer", ["Gui", "UiPlugin", "Widgets", "Xml"])
            _create_module("Help", ["Gui", "Sql", "Widgets"])

        if self.options.qtquick3d and self.options.gui:
            _create_module("Quick3DUtils", ["Gui"])
            _create_module("Quick3DRender", ["Quick3DUtils", "Quick"])
            _create_module("Quick3DAssetImport", ["Gui", "Qml", "Quick3DRender", "Quick3DUtils"])
            _create_module("Quick3DRuntimeRender", ["Quick3DRender", "Quick3DAssetImport", "Quick3DUtils"])
            _create_module("Quick3D", ["Gui", "Qml", "Quick", "Quick3DRuntimeRender"])

        if self.options.qtquickcontrols2 and self.options.gui:
            _create_module("QuickControls2", ["Gui", "Quick"])
            _create_module("QuickTemplates2", ["Gui", "Quick"])

        if self.options.gui and self.options.get_safe("qtsvg"):
            _create_module("Svg", ["Gui"])
            _create_plugin("QSvgIconPlugin", "qsvgicon", "iconengines", [])
            _create_plugin("QSvgPlugin", "qsvg", "imageformats", [])

        if self.options.gui:
            jpeg_lib = self.options.get_safe("with_libjpeg")
            if jpeg_lib:
                _create_plugin("QJpegPlugin", "qjpeg", "imageformats", [f"{jpeg_lib}::{jpeg_lib}"])

        if self.options.gui and self.options.get_safe("qtwayland"):
            _create_module("WaylandClient", ["Gui", "wayland::wayland-client"])
            if Version(self.version) >= "5.8":
                _create_module("WaylandCompositor", ["Gui", "wayland::wayland-server"])

            def _wl_plugin(pluginname, libname, plugintype, requires):
                # Qt 5.6.3's qtwayland builds only a subset of these plugins for
                # the RDK GLES2/no-X11 config; declare each only if its lib was
                # packaged so CMakeConfigDeps can resolve every component location.
                so = os.path.join(self.package_folder, "plugins", plugintype, f"lib{libname}.so")
                if os.path.isfile(so):
                    _create_plugin(pluginname, libname, plugintype, requires)

            _wl_plugin("QWaylandIntegrationPlugin","qwayland-generic", "platforms", ["Gui"])
            _wl_plugin("QWaylandEglPlatformIntegrationPlugin","qwayland-egl", "platforms", ["Gui"])
            _wl_plugin("QWaylandXCompositeGlxPlatformIntegrationPlugin","qwayland-xcomposite-glx", "platforms", ["Gui"])
            _wl_plugin("QWaylandWlShellIntegrationPlugin","wl-shell", "wayland-shell-integration", ["WaylandClient"])
            _wl_plugin("QWaylandFullScreenShellV1IntegrationPlugin","fullscreen-shell-v1", "wayland-shell-integration", ["WaylandClient"])
            _wl_plugin("QWaylandXdgShellIntegrationPlugin","xdg-shell", "wayland-shell-integration", ["WaylandClient"])
            _wl_plugin("QWaylandIviShellIntegrationPlugin","ivi-shell", "wayland-shell-integration", ["WaylandClient"])
            _wl_plugin("QWaylandEglClientBufferPlugin", "qt-plugin-wayland-egl", "wayland-graphics-integration-client", ["WaylandClient"])
            _wl_plugin("QWaylandXCompositeGlxClientBufferPlugin", "xcomposite-glx", "wayland-graphics-integration-client", ["WaylandClient"])
            _wl_plugin("QWaylandBradientDecorationPlugin", "bradient", "wayland-decoration-client", ["WaylandClient"])

        if self.options.qtlocation:
            _create_module("Positioning")
            _create_module("Location", ["Gui", "Quick"])
            _create_plugin("QGeoServiceProviderFactoryMapbox", "qtgeoservices_mapbox", "geoservices", [])
            _create_plugin("QGeoServiceProviderFactoryMapboxGL", "qtgeoservices_mapboxgl", "geoservices", [])
            _create_plugin("GeoServiceProviderFactoryEsri", "qtgeoservices_esri", "geoservices", [])
            _create_plugin("QGeoServiceProviderFactoryItemsOverlay", "qtgeoservices_itemsoverlay", "geoservices", [])
            _create_plugin("QGeoServiceProviderFactoryNokia", "qtgeoservices_nokia", "geoservices", [])
            _create_plugin("QGeoServiceProviderFactoryOsm", "qtgeoservices_osm", "geoservices", [])
            _create_plugin("QGeoPositionInfoSourceFactoryGeoclue", "qtposition_geoclue", "position", [])
            _create_plugin("QGeoPositionInfoSourceFactoryGeoclue2", "qtposition_geoclue2", "position", [])
            _create_plugin("QGeoPositionInfoSourceFactoryPoll", "qtposition_positionpoll", "position", [])
            _create_plugin("QGeoPositionInfoSourceFactorySerialNmea", "qtposition_serialnmea", "position", [])

        if self.options.qtwebchannel:
            _create_module("WebChannel", ["Qml"])

        if self.options.qtwebengine:
            webenginereqs = ["Gui", "Quick", "WebChannel", "Positioning"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                webenginereqs.extend(["expat::expat", "opus::libopus", "xorg-proto::xorg-proto", "libxshmfence::libxshmfence", \
                                      "nss::nss", "libdrm::libdrm", "egl::egl"])
            _create_module("WebEngineCore", webenginereqs)
            if self.settings.os != "Windows":
                self.cpp_info.components["WebEngineCore"].system_libs.append("resolv")
            _create_module("WebEngine", ["WebEngineCore"])
            _create_module("WebEngineWidgets", ["WebEngineCore", "Quick", "PrintSupport", "Widgets", "Gui", "Network"])

        if self.options.qtserialport:
            _create_module("SerialPort")

        if self.options.qtserialbus:
            _create_module("SerialBus", ["SerialPort"] if self.options.get_safe("qtserialport") else [])
            _create_plugin("PassThruCanBusPlugin", "qtpassthrucanbus", "canbus", [])
            _create_plugin("PeakCanBusPlugin", "qtpeakcanbus", "canbus", [])
            _create_plugin("SocketCanBusPlugin", "qtsocketcanbus", "canbus", [])
            _create_plugin("TinyCanBusPlugin", "qttinycanbus", "canbus", [])
            _create_plugin("VirtualCanBusPlugin", "qtvirtualcanbus", "canbus", [])

        if self.options.qtsensors:
            _create_module("Sensors")
            _create_plugin("genericSensorPlugin", "qtsensors_generic", "sensors", [])
            _create_plugin("IIOSensorProxySensorPlugin", "qtsensors_iio-sensor-proxy", "sensors", [])
            if self.settings.os == "Linux":
                _create_plugin("LinuxSensorPlugin", "qtsensors_linuxsys", "sensors", [])
            _create_plugin("QtSensorGesturePlugin", "qtsensorgestures_plugin", "sensorgestures", [])
            _create_plugin("QShakeSensorGesturePlugin", "qtsensorgestures_shakeplugin", "sensorgestures", [])

        if self.options.qtscxml:
            _create_module("Scxml", ["Qml"])
            _add_build_module("qtScxml", self._cmake_qt5_private_file("Scxml"))

        if self.options.qtpurchasing:
            _create_module("Purchasing")

        if self.options.qtcharts:
            _create_module("Charts", ["Gui", "Widgets"])

        if self.options.qtgamepad:
            _create_module("Gamepad", ["Gui"])
            if self.settings.os == "Linux":
                _create_plugin("QEvdevGamepadBackendPlugin", "evdevgamepad", "gamepads", [])
            if self.settings.os == "Macos":
                _create_plugin("QDarwinGamepadBackendPlugin", "darwingamepad", "gamepads", [])
            if self.settings.os =="Windows":
                _create_plugin("QXInputGamepadBackendPlugin", "xinputgamepad", "gamepads", [])

        if self.options.qt3d:
            _create_module("3DCore", ["Gui", "Network"])

            _create_module("3DRender", ["3DCore"])
            _create_plugin("DefaultGeometryLoaderPlugin", "defaultgeometryloader", "geometryloaders", [])
            _create_plugin("GLTFGeometryLoaderPlugin", "gltfgeometryloader", "geometryloaders", [])
            _create_plugin("GLTFSceneExportPlugin", "gltfsceneexport", "sceneparsers", [])
            _create_plugin("GLTFSceneImportPlugin", "gltfsceneimport", "sceneparsers", [])
            _create_plugin("OpenGLRendererPlugin", "openglrenderer", "renderers", [])
            _create_plugin("Scene2DPlugin", "scene2d", "renderplugins", [])

            _create_module("3DAnimation", ["3DRender", "3DCore", "Gui"])
            _create_module("3DInput", ["3DCore", "Gui"] + (["Gamepad"] if self.options.qtgamepad else []))
            _create_module("3DLogic", ["3DCore", "Gui"])
            _create_module("3DExtras", ["3DRender", "3DInput", "3DLogic", "3DCore", "Gui"])
            _create_module("3DQuick", ["3DCore", "Quick", "Gui", "Qml"])
            _create_module("3DQuickAnimation", ["3DAnimation", "3DRender", "3DQuick", "3DCore", "Gui", "Qml"])
            _create_module("3DQuickExtras", ["3DExtras", "3DInput", "3DQuick", "3DRender", "3DLogic", "3DCore", "Gui", "Qml"])
            _create_module("3DQuickInput", ["3DInput", "3DQuick", "3DCore", "Gui", "Qml"])
            _create_module("3DQuickRender", ["3DRender", "3DQuick", "3DCore", "Gui", "Qml"])
            _create_module("3DQuickScene2D", ["3DRender", "3DQuick", "3DCore", "Gui", "Qml"])

        if self.options.qtmultimedia:
            multimedia_reqs = ["Network", "Gui"]
            if self.options.get_safe("with_libalsa", False):
                multimedia_reqs.append("libalsa::libalsa")
            if self.options.with_openal:
                multimedia_reqs.append("openal-soft::openal-soft")
            if self.options.get_safe("with_pulseaudio", False):
                multimedia_reqs.append("pulseaudio::pulse")
            _create_module("Multimedia", multimedia_reqs)
            _create_module("MultimediaWidgets", ["Multimedia", "Widgets", "Gui"])
            if self.options.qtdeclarative and self.options.gui:
                _create_module("MultimediaQuick", ["Multimedia", "Quick"])
            _create_plugin("QM3uPlaylistPlugin", "qtmultimedia_m3u", "playlistformats", [])
            if self.options.with_gstreamer:
                _create_module("MultimediaGstTools", ["Multimedia", "MultimediaWidgets", "Gui", "gst-plugins-base::gst-plugins-base"])
                _create_plugin("QGstreamerAudioDecoderServicePlugin", "gstaudiodecoder", "mediaservice", [])
                _create_plugin("QGstreamerCaptureServicePlugin", "gstmediacapture", "mediaservice", [])
                _create_plugin("QGstreamerPlayerServicePlugin", "gstmediaplayer", "mediaservice", [])
            if self.settings.os == "Linux":
                if self.options.with_gstreamer:
                    _create_plugin("CameraBinServicePlugin", "gstcamerabin", "mediaservice", [])
                if self.options.get_safe("with_libalsa", False):
                    _create_plugin("QAlsaPlugin", "qtaudio_alsa", "audio", [])
            if self.settings.os == "Windows":
                _create_plugin("AudioCaptureServicePlugin", "qtmedia_audioengine", "mediaservice", [])
                _create_plugin("DSServicePlugin", "dsengine", "mediaservice", [])
                _create_plugin("QWindowsAudioPlugin", "qtaudio_windows", "audio", [])
            if self.settings.os == "Macos":
                _create_plugin("AudioCaptureServicePlugin", "qtmedia_audioengine", "mediaservice", [])
                _create_plugin("AVFMediaPlayerServicePlugin", "qavfmediaplayer", "mediaservice", [])
                _create_plugin("AVFServicePlugin", "qavfcamera", "mediaservice", [])
                _create_plugin("CoreAudioPlugin", "qtaudio_coreaudio", "audio", [])

        if self.options.qtwebsockets:
            _create_module("WebSockets", ["Network"])

        if self.options.qtconnectivity:
            _create_module("Bluetooth", ["Network"])
            _create_module("Nfc", [])

        if self.options.qtdatavis3d:
            _create_module("DataVisualization", ["Gui"])

        if self.options.qtnetworkauth:
            _create_module("NetworkAuth", ["Network"])

        if self.settings.os != "Windows":
            self.cpp_info.components["qtCore"].cxxflags.append("-fPIC")

        if self.options.get_safe("qtx11extras"):
            _create_module("X11Extras")

        if self.options.qtremoteobjects:
            _create_module("RemoteObjects")

        if self.options.get_safe("qtwinextras"):
            _create_module("WinExtras")

        if self.options.get_safe("qtmacextras"):
            _create_module("MacExtras")

        if self.options.qtxmlpatterns:
            _create_module("XmlPatterns", ["Network"])

        if self.options.get_safe("qtactiveqt"):
            _create_module("AxBase", ["Gui", "Widgets"])
            self.cpp_info.components["qtAxBase"].includedirs = ["include", os.path.join("include", "ActiveQt")]
            self.cpp_info.components["qtAxBase"].system_libs.extend(["ole32", "oleaut32", "user32", "gdi32", "advapi32"])
            if self.settings.compiler == "gcc":
                self.cpp_info.components["qtAxBase"].system_libs.append("uuid")
            _create_module("AxContainer", ["Core", "Gui", "Widgets", "AxBase"])
            self.cpp_info.components["qtAxContainer"].includedirs = [os.path.join("include", "ActiveQt")]
            _create_module("AxServer", ["Core", "Gui", "Widgets", "AxBase"])
            self.cpp_info.components["qtAxServer"].includedirs = [os.path.join("include", "ActiveQt")]
            self.cpp_info.components["qtAxServer"].system_libs.append("shell32")

        if self.options.qtscript:
            _create_module("Script")
            if self.options.widgets:
                _create_module("ScriptTools", ["Gui", "Widgets", "Script"])

        if self.options.qtandroidextras:
            _create_module("AndroidExtras")

        if self.options.qtwebview:
            _create_module("WebView", ["Gui", "Quick"])

        if self.options.qtvirtualkeyboard:
            _create_module("VirtualKeyboard", ["Qml", "Quick", "Gui"])

        if self.options.qtspeech:
            _create_module("TextToSpeech")

        if not self.options.shared:
            if self.settings.os == "Windows":
                self.cpp_info.components["qtCore"].system_libs.append("version")  # qtcore requires "GetFileVersionInfoW" and "VerQueryValueW" which are in "Version.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("winmm")    # qtcore requires "__imp_timeSetEvent" which is in "Winmm.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("netapi32") # qtcore requires "NetApiBufferFree" which is in "Netapi32.lib" library
                self.cpp_info.components["qtCore"].system_libs.append("userenv")  # qtcore requires "__imp_GetUserProfileDirectoryW " which is in "UserEnv.Lib" library
                self.cpp_info.components["qtCore"].system_libs.append("ws2_32")  # qtcore requires "WSAStartup " which is in "Ws2_32.Lib" library
                self.cpp_info.components["qtNetwork"].system_libs.append("dnsapi")  # qtnetwork from qtbase requires "DnsFree" which is in "Dnsapi.lib" library
                self.cpp_info.components["qtNetwork"].system_libs.append("iphlpapi")
                if self.options.widgets:
                    self.cpp_info.components["qtWidgets"].system_libs.append("uxtheme")
                    self.cpp_info.components["qtWidgets"].system_libs.append("dwmapi")
                if self.options.get_safe("qtwinextras"):
                    self.cpp_info.components["qtWinExtras"].system_libs.append("dwmapi")  # qtwinextras requires "DwmGetColorizationColor" which is in "dwmapi.lib" library

            if is_apple_os(self):
                self.cpp_info.components["qtCore"].frameworks.append("CoreServices" if self.settings.os == "Macos" else "MobileCoreServices")
                self.cpp_info.components["qtNetwork"].frameworks.append("SystemConfiguration")
                if self.options.with_gssapi:
                    self.cpp_info.components["qtNetwork"].frameworks.append("GSS")
                if not self.options.get_safe("openssl", False): # with SecureTransport
                    self.cpp_info.components["qtNetwork"].frameworks.append("Security")
            if self.settings.os == "Macos" or (self.settings.os == "iOS" and Version(self.settings.compiler.version) >= "14.0"):
                self.cpp_info.components["qtCore"].frameworks.append("IOKit")     # qtcore requires "_IORegistryEntryCreateCFProperty", "_IOServiceGetMatchingService" and much more which are in "IOKit" framework
            if self.settings.os == "Macos":
                self.cpp_info.components["qtCore"].frameworks.append("Cocoa")     # qtcore requires "_OBJC_CLASS_$_NSApplication" and more, which are in "Cocoa" framework
                self.cpp_info.components["qtCore"].frameworks.append("Security")  # qtcore requires "_SecRequirementCreateWithString" and more, which are in "Security" framework

        self.cpp_info.components["qtCore"].builddirs.append(os.path.join("bin"))
        _add_build_module("qtCore", self._cmake_core_extras_file)
        _add_build_module("qtCore", self._cmake_qt5_private_file("Core"))

        for m in os.listdir(os.path.join("lib", "cmake")):
            module = os.path.join("lib", "cmake", m, f"{m}Macros.cmake")
            component_name = m.replace("Qt5", "qt")
            if os.path.isfile(module):
                _add_build_module(component_name, module)
            self.cpp_info.components[component_name].builddirs.append(os.path.join("lib", "cmake", m))

        qt5core_config_extras_mkspec_dir_cmake = load(self,
            os.path.join("lib", "cmake", "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake"))
        mkspecs_dir_begin = qt5core_config_extras_mkspec_dir_cmake.find("mkspecs/")
        mkspecs_dir_end = qt5core_config_extras_mkspec_dir_cmake.find("\"", mkspecs_dir_begin)
        mkspecs_path = qt5core_config_extras_mkspec_dir_cmake[mkspecs_dir_begin:mkspecs_dir_end]
        assert os.path.exists(mkspecs_path)
        self.cpp_info.components["qtCore"].includedirs.append(mkspecs_path)

        objects_dirs = glob.glob(os.path.join(self.package_folder, "lib", "objects-*/"))
        for object_dir in objects_dirs:
            for m in os.listdir(object_dir):
                component = "qt" + m[:m.find("_")]
                if component not in self.cpp_info.components:
                    continue
                submodules_dir = os.path.join(object_dir, m)
                for sub_dir in os.listdir(submodules_dir):
                    submodule_dir = os.path.join(submodules_dir, sub_dir)
                    obj_files = [os.path.join(submodule_dir, file) for file in os.listdir(submodule_dir)]
                    self.cpp_info.components[component].exelinkflags.extend(obj_files)
                    self.cpp_info.components[component].sharedlinkflags.extend(obj_files)

        build_modules_list = []

        def _add_build_modules_for_component(component):
            for req in self.cpp_info.components[component].requires:
                if "::" in req: # not a qt component
                    continue
                _add_build_modules_for_component(req)
            build_modules_list.extend(build_modules.pop(component, []))

        for c in self.cpp_info.components:
            _add_build_modules_for_component(c)

        self.cpp_info.set_property("cmake_build_modules", build_modules_list)

    @staticmethod
    def _remove_duplicate(l):
        seen = set()
        seen_add = seen.add
        for element in itertools.filterfalse(seen.__contains__, l):
            seen_add(element)
            yield element

    def _gather_libs(self, p):
        libs = ["-l" + i for i in p.cpp_info.aggregated_components().libs + p.cpp_info.aggregated_components().system_libs]
        if p.ref.name == "libpq" and self.settings.os == "Windows" and Version(p.ref.version) >= "17":
            # libpq/17.x uses Meson filename conventions, pass full filenames instead of "-l" flags
            ext = "lib" if p.options.shared else "a"
            libs = [f"lib{lib}.{ext}" for lib in p.cpp_info.aggregated_components().libs]
            libs.extend([f"{lib}.lib" for lib in p.cpp_info.aggregated_components().system_libs])
        if is_apple_os(self):
            libs += ["-framework " + i for i in p.cpp_info.aggregated_components().frameworks]
        libs += p.cpp_info.aggregated_components().sharedlinkflags
        for dep in p.dependencies.direct_host.values():
            libs += self._gather_libs(dep)
        return self._remove_duplicate(libs)
