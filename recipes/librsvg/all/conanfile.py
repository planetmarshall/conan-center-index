import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools import files, scm, layout
from conans.tools import run_environment


required_conan_version = ">=1.50.0"


class librsvgConan(ConanFile):
    name = "librsvg"
    description = "A library to render SVG images to Cairo surfaces."
    topics = ("gnome", "svg")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gitlab.gnome.org/GNOME/librsvg"
    license = "LGPL-2.1"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": True,
        "fPIC": True
    }
    win_bash = True

    #short_paths = True

    def layout(self):
        layout.basic_layout(self, src_folder="source")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        env = VirtualBuildEnv(self)
        env.generate(scope="build")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def source(self):
        files.get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build_requirements(self):
        self.tool_requires("automake/1.16.5")
        self.tool_requires("libtool/2.4.7")

    def build(self):
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["librsvg"]
