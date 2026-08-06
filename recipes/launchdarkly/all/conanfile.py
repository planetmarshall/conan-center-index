from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, rm, rmdir, export_conandata_patches, apply_conandata_patches
from conan.tools.build import check_min_cppstd
from conan.tools.files import get
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeConfigDeps, CMakeToolchain, cmake_layout

import os

required_conan_version = ">=2.0.0"


class LaunchDarklyConan(ConanFile):
    name = "launchdarkly"
    description = ("LaunchDarkly is a feature management platform that serves trillions of "
                   "feature flags daily to help teams build better software, faster.")
    license = "Apache-2.0"
    url = "https://github.com/launchdarkly/cpp-sdks"
    homepage = "https://github.com/launchdarkly/cpp-sdks"
    package_type = "library"
    user = "sky"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True
    }

    implements = ["auto_shared_fpic"]

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

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[>=1.81.0 <2]", force=True, transitive_headers=True)
        self.requires("certify/cci.20201114")
        self.requires("openssl/[>=3 <4]", transitive_headers=True)
        self.requires("tl-expected/[>=1.1.0 <2]", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, self._min_cppstd)

        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables.update({
            "BUILD_TESTING": False,
            "LD_BUILD_EXAMPLES": False,
            "LD_BUILD_SHARED_LIBS": self.options.shared,
            "LD_DYNAMIC_LINK_OPENSSL": self.dependencies["openssl"].options.shared,
            "LD_DYNAMIC_LINK_BOOST": self.dependencies["boost"].options.shared,
            "FETCHCONTENT_TRY_FIND_PACKAGE_MODE": "ALWAYS"
        })
        tc.generate()

        deps = CMakeConfigDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="launchdarkly-cpp-client")

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        # remove install cmake files. Conan takes care of cmake support
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["launchdarkly-cpp-client"]
        self.cpp_info.set_property("cmake_file_name", "launchdarkly")
        self.cpp_info.set_property("cmake_target_name", "launchdarkly::launchdarkly-cpp-client")

        self.cpp_info.requires = [
            "certify::certify",
            "openssl::openssl",
            "tl-expected::tl-expected",
            "boost::headers",
            "boost::json",
            "boost::url"
        ]

        # If they are needed on Linux, m, pthread and dl are usually needed on FreeBSD too
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
            self.cpp_info.system_libs.append("pthread")
            self.cpp_info.system_libs.append("dl")
        if self.settings.os == "Macos":
            self.cpp_info.frameworks += ["CoreFoundation", "Security"]
