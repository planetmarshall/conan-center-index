from conan import ConanFile
from conan.tools.scm import Version
from conan.tools import files

from conans import Meson
from conans import tools
from conan.errors import ConanInvalidConfiguration

import os

required_conan_version = ">=1.50.0"


class GtkConan(ConanFile):
    name = "gtk"
    description = "libraries used for creating graphical user interfaces for applications."
    topics = ("gtk", "widgets")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.gtk.org"
    license = "LGPL-2.1-or-later"
    generators = "pkg_config"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_pango": [True, False],
        "with_ffmpeg": [True, False],
        "with_gstreamer": [True, False],
        "with_cups": [True, False],
        "with_cloudprint": [True, False]
        }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_wayland": False,
        "with_x11": True,
        "with_pango": True,
        "with_ffmpeg": False,
        "with_gstreamer": False,
        "with_cups": False,
        "with_cloudprint": False
    }

    short_paths = True

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    @property
    def _gtk4(self):
        return Version("4.0.0") <= Version(self.version) < Version("5.0.0")

    @property
    def _gtk3(self):
        return Version("3.0.0") <= Version(self.version) < Version("4.0.0")

    def export_sources(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # Fix duplicate definitions of DllMain
            self.options["gdk-pixbuf"].shared = True
            # Fix segmentation fault
            self.options["cairo"].shared = True
        if Version(self.version) >= "4.1.0":
            # The upstream meson file does not create a static library
            # See https://github.com/GNOME/gtk/commit/14f0a0addb9a195bad2f8651f93b95450b186bd6
            self.options.shared = True
        if self.settings.os != "Linux":
            del self.options.with_wayland
            del self.options.with_x11

    def validate(self):
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration("this recipes does not support GCC before version 5. contributions are welcome")
        if str(self.settings.compiler) in ["Visual Studio", "msvc"]:
            if Version(self.version) < "4.2":
                raise ConanInvalidConfiguration("MSVC support of this recipe requires at least gtk/4.2")
            if not self.options["glib"].shared:
                raise ConanInvalidConfiguration(f"{self.name} recipe requires shared glib")
            if not self.options["gdk-pixbuf"].shared:
                raise ConanInvalidConfiguration("MSVC build requires shared gdk-pixbuf")
            if not self.options["cairo"].shared:
                raise ConanInvalidConfiguration("MSVC build requires shared cairo")
        if Version(self.version) >= "4.1.0":
            if not self.options.shared:
                raise ConanInvalidConfiguration("gtk supports only shared since 4.1.0")

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.os == "Linux":
            if self.options.with_wayland or self.options.with_x11:
                if not self.options.with_pango:
                    raise ConanInvalidConfiguration("with_pango option is mandatory when with_wayland or with_x11 is used")

    def build_requirements(self):
        self.build_requires("meson/0.62.2")
        if self._gtk4:
            self.build_requires("libxml2/2.9.14") # for xmllint
        self.build_requires("pkgconf/1.7.4")
        if self._gtk4:
            self.build_requires("sassc/3.6.2")

    def requirements(self):
        self.requires("gdk-pixbuf/2.42.8")
        self.requires("glib/2.73.0")
        if self._gtk4 or self.settings.compiler != "Visual Studio":
            self.requires("cairo/1.17.4")
        if self._gtk4:
            self.requires("graphene/1.10.8")
            self.requires("fribidi/1.0.12")
            self.requires("libpng/1.6.37")
            self.requires("libtiff/4.3.0")
            self.requires("libjpeg/9d")
        if self.settings.os == "Linux":
            if self._gtk4:
                self.requires("xkbcommon/1.4.1")
            if self._gtk3:
                self.requires("at-spi2-atk/2.38.0")
            if self.options.with_wayland:
                if self._gtk3:
                    self.requires("xkbcommon/1.4.1")
                self.requires("wayland/1.20.0")
            if self.options.with_x11:
                self.requires("xorg/system")
        if self._gtk3:
            self.requires("atk/2.38.0")
        self.requires("libepoxy/1.5.10")
        if self.options.with_pango:
            self.requires("pango/1.50.7")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/5.0")
        if self.options.with_gstreamer:
            self.requires("gstreamer/1.19.2")

    def source(self):
        files.get(self, **self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder)

    def _configure_meson(self):
        meson = Meson(self)
        defs = {}
        if self.settings.os == "Linux":
            defs["wayland_backend" if self._gtk3 else "wayland-backend"] = "true" if self.options.with_wayland else "false"
            defs["x11_backend" if self._gtk3 else "x11-backend"] = "true" if self.options.with_x11 else "false"
        defs["introspection"] = "false" if self._gtk3 else "disabled"
        defs["gtk_doc"] = "false"
        defs["man-pages" if self._gtk4 else "man"] = "false"
        defs["tests" if self._gtk3 else "build-tests"] = "false"
        defs["examples" if self._gtk3 else "build-examples"] = "false"
        defs["demos"] = "false"
        defs["datadir"] = os.path.join(self.package_folder, "res", "share")
        defs["localedir"] = os.path.join(self.package_folder, "res", "share", "locale")
        defs["sysconfdir"] = os.path.join(self.package_folder, "res", "etc")

        if self._gtk4:
            def enabled(opt):
                return "enabled" if opt else "disabled"

            defs["media-ffmpeg"] = enabled(self.options.with_ffmpeg)
            defs["media-gstreamer"] = enabled(self.options.with_gstreamer)
            defs["print-cups"] = enabled(self.options.with_cups)
            if Version(self.version) < "4.3.2":
                defs["print-cloudprint"] = enabled(self.options.with_cloudprint)
        args=[]
        args.append("--wrap-mode=nofallback")
        meson.configure(defs=defs, build_folder=self._build_subfolder, source_folder=self._source_subfolder, pkg_config_paths=[self.install_folder], args=args)
        return meson

    def build(self):
        files.apply_conandata_patches(self)
        if self._gtk3:
            files.replace_in_file(self, os.path.join(self._source_subfolder, "meson.build"), "\ntest(\n", "\nfalse and test(\n")
        if "4.2.0" <= Version(self.version) < "4.6.1":
            files.replace_in_file(self, os.path.join(self._source_subfolder, "meson.build"),
                                  "gtk_update_icon_cache: true",
                                  "gtk_update_icon_cache: false")
        if "4.6.2" <= Version(self.version):
            files.replace_in_file(self, os.path.join(self._source_subfolder, "meson.build"),
                                  "dependency(is_msvc_like ? ",
                                  "dependency(false ? ")
        with tools.environment_append(tools.RunEnvironment(self).vars):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        meson = self._configure_meson()
        with tools.environment_append({
            "PKG_CONFIG_PATH": self.install_folder,
            "PATH": [os.path.join(self.package_folder, "bin")]}):
            meson.install()

        self.copy(pattern="COPYING", src=self._source_subfolder, dst="licenses")
        files.rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        files.rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        files.rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))

    def _build_gdk3_requirements(self):
        requirements = [
            "gdk-pixbuf::gdk-pixbuf",
            "libepoxy::libepoxy"
        ]
        if self.options.with_pango:
            requirements += ["pango::pango_", "pango::pangocairo"]
        if self.settings.compiler != "Visual Studio":
            requirements += ["cairo::cairo", "cairo::cairo-gobject"]
        if self.settings.os == "Linux":
            requirements += ["glib::gio-unix-2.0", "cairo::cairo-xlib"]
            if self.options.with_x11:
                requirements.append("xorg::xorg")
        return requirements

    def _build_gtk3_requirements(self):
        requirements = [
            "gdk-3.0",
            "atk::atk",
            "gdk-pixbuf::gdk-pixbuf",
            "glib::gio-2.0",
            "libepoxy::libepoxy"
        ]
        if self.settings.compiler != "Visual Studio":
            requirements += ["cairo::cairo", "cairo::cairo-gobject"]
        if self.settings.os == "Linux":
            requirements += ["at-spi2-atk::at-spi2-atk", "glib::gio-unix-2.0"]
        if self.options.with_pango:
            requirements.append('pango::pangoft2')
        return requirements

    def _build_gtk4_requirements(self):
        requirements = [
            "cairo::cairo",
            "gdk-pixbuf::gdk-pixbuf",
            "glib::glib",
            "graphene::graphene",
            "fribidi::fribidi",
            "libepoxy::libepoxy",
            "libpng::libpng",
            "libtiff::libtiff",
            "libjpeg::libjpeg"
        ]
        if self.settings.os == "Linux":
            requirements.append("xkbcommon::xkbcommon")
            if self.options.with_wayland:
                requirements.append("wayland::wayland")
            if self.options.with_x11:
                requirements.append("xorg::xorg")

        if self.options.with_pango:
            requirements.append("pango::pango")
        if self.options.with_ffmpeg:
            requirements.append("ffmpeg::ffmpeg")
        if self.options.with_gstreamer:
            requirements.append("gstreamer::gstreamer")

        return requirements

    def package_info(self):
        if self._gtk3:
            self.cpp_info.components["gdk-3.0"].set_property("pkg_config_name", "gdk-3.0")
            self.cpp_info.components["gdk-3.0"].libs = ["gdk-3"]
            self.cpp_info.components["gdk-3.0"].includedirs = [os.path.join("include", "gtk-3.0")]
            self.cpp_info.components["gdk-3.0"].requires = self._build_gdk3_requirements()

            self.cpp_info.components["gtk+-3.0"].set_property("pkg_config_name", "gtk+-3.0")
            self.cpp_info.components["gtk+-3.0"].libs = ["gtk-3"]
            self.cpp_info.components["gtk+-3.0"].includedirs = [os.path.join("include", "gtk-3.0")]
            self.cpp_info.components["gtk+-3.0"].requires = self._build_gtk3_requirements()

            self.cpp_info.components["gail-3.0"].set_property("pkg_config_name", "gail-3.0")
            self.cpp_info.components["gail-3.0"].libs = ["gailutil-3"]
            self.cpp_info.components["gail-3.0"].requires = ["gtk+-3.0", "atk::atk"]
            self.cpp_info.components["gail-3.0"].includedirs = [os.path.join("include", "gail-3.0")]
        elif self._gtk4:
            self.cpp_info.components["gtk4"].set_property("pkg_config_name", "gtk4")
            self.cpp_info.components["gtk4"].requires = self._build_gtk4_requirements()
            self.cpp_info.components["gtk4"].libs = ["gtk-4"]
            self.cpp_info.components["gtk4"].includedirs.append(os.path.join("include", "gtk-4.0"))

            if self.settings.os == "Linux":
                self.cpp_info.components["gtk4-unix-print"].set_property("pkg_config_name", "gtk4-unix-print")
                self.cpp_info.components["gtk4-unix-print"].includedirs.append(os.path.join("include", "gtk-4.0", "unix-print"))
                self.cpp_info.components["gtk4-unix-print"].requires.append("gtk4")
