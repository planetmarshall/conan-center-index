import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm, rmdir
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import check_min_vs, is_msvc
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class GtkmmConan(ConanFile):
    name = "gtkmm"
    description = "gtkmm is the official C++ interface for the popular GUI library GTK"
    topics = ("gtk", "widgets")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.gtkmm.org"
    license = "LGPL-2.1-or-later"
    generators = "pkg_config"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
        }
    default_options = {
        "shared": False,
        "fPIC": True
    }

    @property
    def _min_cppstd(self):
        return 17

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "7",
            "clang": "7",
            "apple-clang": "10",
        }

    #def export_sources(self):
    #    for patch in self.conan_data.get("patches", {}).get(self.version, []):
    #        self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self):
            # Static builds not supported by MSVC
            self.options.shared = True

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        self.options["cairo"].with_glib = True

    def layout(self):
        # src_folder must use the same source folder name the project
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cairomm/1.16.1")
        # gtkmm has a direct dependency on cairo-gobject which is not explicit in the meson configuration
        self.requires("cairo/1.17.6")
        self.requires("glibmm/2.72.1")
        self.requires("glib/2.75.0")
        self.requires("gtk/4.7.0")
        self.requires("libsigcpp/3.0.7")
        self.requires("pangomm/2.50.0")

    def validate(self):
        # validate the minimum cpp standard supported. For C++ projects only
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        check_min_vs(self, 191)
        if not is_msvc(self):
            minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
            if minimum_version and Version(self.settings.compiler.version) < minimum_version:
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
                )
        # in case it does not work in another configuration, it should validated here too
        if is_msvc(self) and self.info.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} can not be built as shared on Visual Studio and msvc.")

    def build_requirements(self):
        self.build_requires("meson/1.2.1")
        self.build_requires("pkgconf/2.0.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.preprocessor_definitions["MYDEFINE"] = "MYDEF_VALUE"
        tc.project_options.update({
            "build-demos": 'false',
            "build-tests": 'false'
        })
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

        tc = VirtualBuildEnv(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _get_msvc_toolset(self):
        if self.settings.compiler.get_safe("toolset"):
            return self.settings.compiler.toolset

        version = str(self.settings.compiler.version)
        toolset_map = {
            "15": "v141",
            "16": "v142",
            "17": "v143"
        }
        if version in toolset_map:
            return toolset_map.get(version)

        raise ConanInvalidConfiguration("Cannot get MSVC compiler toolset information")

    @property
    def _msvc_toolset_suffix(self):
        toolset = self._get_msvc_toolset()
        match = re.match("v([0-9]+)", str(toolset))
        if match is not None:
            return f"vc{match.group(1)}"

        raise ConanInvalidConfiguration("Cannot get MSVC compiler toolset information")

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    @property
    def _libname(self):
        if is_msvc(self):
            return f"gtkmm-{self._msvc_toolset_suffix}-4.0"
        return "gtkmm-4.0"

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gtkmm-4.0")
        self.cpp_info.names["pkg_config"] = "gtkmm-4.0"

        self.cpp_info.requires = ["cairo::cairo-gobject"]
        self.cpp_info.libs = [self._libname]
        self.cpp_info.includedirs += [
            os.path.join("include", "gtkmm-4.0"),
            os.path.join("lib", "gtkmm-4.0", "include")
        ]
