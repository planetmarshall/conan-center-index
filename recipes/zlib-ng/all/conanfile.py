from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
import os

required_conan_version = ">=1.53.0"


class ZlibNgConan(ConanFile):
    name = "zlib-ng"
    description = "zlib data compression library for the next generation systems"
    license ="Zlib"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/zlib-ng/zlib-ng/"
    topics = ("zlib", "compression")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "zlib_compat": [True, False],
        "with_gzfileop": [True, False],
        "with_optim": [True, False],
        "with_new_strategies": [True, False],
        "with_native_instructions": [True, False],
        "with_reduced_mem": [True, False],
        "with_runtime_cpu_detection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "zlib_compat": False,
        "with_gzfileop": True,
        "with_optim": True,
        "with_new_strategies": True,
        "with_native_instructions": False,
        "with_reduced_mem": False,
        "with_runtime_cpu_detection": True,
    }
    
    @property
    def _is_windows(self):
        return self.settings.os in ["Windows", "WindowsStore"]

    def config_options(self):
        if self._is_windows:
            del self.options.fPIC
        if Version(self.version) < "2.1.0":
            del self.options.with_reduced_mem
        if Version(self.version) < "2.2.1":
            del self.options.with_runtime_cpu_detection

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")
        if self.options.zlib_compat:
            self.provides = ["zlib"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.info.options.zlib_compat and not self.info.options.with_gzfileop:
            raise ConanInvalidConfiguration("The option 'with_gzfileop' must be True when 'zlib_compat' is True.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ZLIB_ENABLE_TESTS"] = False
        tc.variables["ZLIBNG_ENABLE_TESTS"] = False

        tc.variables["ZLIB_COMPAT"] = self.options.zlib_compat
        tc.variables["WITH_GZFILEOP"] = self.options.with_gzfileop
        tc.variables["WITH_OPTIM"] = self.options.with_optim
        tc.variables["WITH_NEW_STRATEGIES"] = self.options.with_new_strategies
        tc.variables["WITH_NATIVE_INSTRUCTIONS"] = self.options.with_native_instructions
        if Version(self.version) >= "2.1.0":
            tc.variables["WITH_REDUCED_MEM"] = self.options.with_reduced_mem
        if Version(self.version) >= "2.2.1":
            tc.variables["WITH_RUNTIME_CPU_DETECTION"] = self.options.with_runtime_cpu_detection
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        license_folder = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.md", src=self.source_folder, dst=license_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # upstream CMakeLists intentionally hardcodes install_name with full
        # install path (to match autootools behavior), instead of @rpath
        fix_apple_shared_install_name(self)

    def package_info(self):
        #FIXME: CMake targets are https://github.com/zlib-ng/zlib-ng/blob/29fd4672a2279a0368be936d7cd44d013d009fae/CMakeLists.txt#L914
        suffix = "" if self.options.zlib_compat else "-ng"
        self.cpp_info.set_property("pkg_config_name", f"zlib{suffix}")
        if self._is_windows:
            # The library name of zlib-ng is complicated in zlib-ng>=2.0.4:
            # https://github.com/zlib-ng/zlib-ng/blob/2.0.4/CMakeLists.txt#L994-L1016
            base = "zlib" if is_msvc(self) or Version(self.version) < "2.0.4" or self.options.shared else "z"
            static_flag = "static" if is_msvc(self) and not self.options.shared and Version(self.version) >= "2.0.4" else ""
            build_type = "d" if self.settings.build_type == "Debug" else ""
            self.cpp_info.libs = [f"{base}{static_flag}{suffix}{build_type}"]
        else:
            self.cpp_info.libs = [f"z{suffix}"]
        if self.options.zlib_compat:
            self.cpp_info.defines.append("ZLIB_COMPAT")
            #copied from zlib
            self.cpp_info.set_property("cmake_find_mode", "both")
            self.cpp_info.set_property("cmake_file_name", "ZLIB")
            self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
            self.cpp_info.names["cmake_find_package"] = "ZLIB"
            self.cpp_info.names["cmake_find_package_multi"] = "ZLIB"
        if self.options.with_gzfileop:
            self.cpp_info.defines.append("WITH_GZFILEOP")
        if not self.options.with_new_strategies:
            self.cpp_info.defines.extend(["NO_QUICK_STRATEGY", "NO_MEDIUM_STRATEGY"])
