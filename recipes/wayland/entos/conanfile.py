from pathlib import Path

from conan import ConanFile, Version
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import PkgConfig

required_conan_version = ">=1.53.0"


class WaylandEntosConan(ConanFile):
    r"""
    Entos sysroot package wrapper for Wayland. Allows us to override any Wayland
    requirements in the dependency graph with a package in a defined sysroot
    (defined in config tools.build:sysroot)
    """

    name = "wayland"
    description = (
        "Wayland is a project to define a protocol for a compositor to talk to "
        "its clients as well as a library implementation of the protocol"
    )
    topics = "protocol", "compositor", "display"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://wayland.freedesktop.org"
    license = "MIT"
    package_type = "library"
    # we need to set this here, as we can't determine it from the sysroot
    # at the point where we need it
    version = "1.20.0"
    user = "entos"
    settings = "os", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_libraries": [True, False],
        "enable_dtd_validation": [True, False],
        "enable_scanner": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "enable_libraries": True,
        "enable_dtd_validation": True,
        "enable_scanner": False,
    }

    @property
    def _sysroot(self) -> Path:
        return Path(str(self.conf.get("tools.build:sysroot")))

    def _pkgconf(self):
        return PkgConfig(
            self,
            "wayland-client",
            pkg_config_path=(self._sysroot / "usr" / "lib" / "pkgconfig").as_posix(),
        )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def package_info(self):
        if not self._sysroot.exists():
            raise ConanInvalidConfiguration(
                    f"Sysroot path '{self._sysroot}' does not exist"
                )

        pkgconf = self._pkgconf()
        # sanity check. We can't just set the version from the pkg-config file
        # using `set_version` as version setting is done very early in the conan process, when we don't
        # yet have access to profile information
        if Version(self.version) != Version(pkgconf.version):
            self.output.error(
                f"Version of wayland in Entos sysroot ({pkgconf.version}) does not match recipe version {self.version}"
            )

        include_dir = (self._sysroot / Path(pkgconf.variables["includedir"]).relative_to("/")).as_posix()
        lib_dir = (self._sysroot / Path(pkgconf.variables["libdir"]).relative_to("/")).as_posix()

        self.cpp_info.components["wayland-client"].libs = ["wayland-client"]
        self.cpp_info.components["wayland-client"].set_property(
            "pkg_config_name", "wayland-client"
        )
        self.cpp_info.components["wayland-client"].system_libs = ["pthread", "m"]
        self.cpp_info.components["wayland-client"].includedirs = [include_dir]
        self.cpp_info.components["wayland-client"].libdirs = [lib_dir]
        self.cpp_info.components["wayland-client"].system_libs += ["rt"]
        self.cpp_info.components["wayland-client"].set_property(
            "component_version", self.version
        )

        self.cpp_info.components["wayland-cursor"].libs = ["wayland-cursor"]
        self.cpp_info.components["wayland-cursor"].set_property(
            "pkg_config_name", "wayland-cursor"
        )
        self.cpp_info.components["wayland-cursor"].requires = ["wayland-client"]
        self.cpp_info.components["wayland-cursor"].set_property(
            "component_version", self.version
        )
        self.cpp_info.components["wayland-cursor"].includedirs = [include_dir]
        self.cpp_info.components["wayland-cursor"].libdirs = [lib_dir]

        self.cpp_info.components["wayland-egl"].libs = ["wayland-egl"]
        self.cpp_info.components["wayland-egl"].set_property(
            "pkg_config_name", "wayland-egl"
        )
        self.cpp_info.components["wayland-egl"].requires = ["wayland-client"]
        self.cpp_info.components["wayland-egl"].includedirs = [include_dir]
        self.cpp_info.components["wayland-egl"].libdirs = [lib_dir]

        self.cpp_info.components["wayland-egl-backend"].set_property(
            "pkg_config_name", "wayland-egl-backend"
        )
        self.cpp_info.components["wayland-egl-backend"].includedirs = [include_dir]
        self.cpp_info.components["wayland-egl-backend"].libdirs = [lib_dir]
