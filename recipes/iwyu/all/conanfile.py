from pathlib import Path

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeConfigDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    copy,
    get,
    rmdir,
)


required_conan_version = ">=2.25.0"


class IwyuConan(ConanFile):
    name = "iwyu"
    description = "A tool to ensure C++ source files include the appropriate headers"
    license = "DocumentRef-LICENSE.TXT-LicenseRef-iwyu"
    homepage = "https://github.com/include-what-you-use/include-what-you-use"
    url = "https://github.com/conan-io/conan-center-index"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Always prefer self.requirements() method instead of self.requires attribute.
        llvm_version = {"0.25": "21.1.8"}.get(str(self.version), "21.1.8")
        self.requires(f"clang/{llvm_version}")
        self.requires(f"llvm-core/{llvm_version}")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        clang = self.dependencies["clang"]
        tc.cache_variables["IWYU_LINK_CLANG_DYLIB"] = bool(clang.options.shared)
        tc.cache_variables["IWYU_RESOURCE_RELATIVE_TO"] = "iwyu"
        tc.generate()

        deps = CMakeConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package_id(self):
        del self.info.settings.compiler

    def package(self):
        package_folder = Path(self.package_folder)
        copy(
            self,
            "LICENSE.TXT",
            self.source_folder,
            (package_folder / "licenses").as_posix(),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, (package_folder / "share" / "man").as_posix())
        clang = self.dependencies["clang"]

        copy(
            self,
            "*",
            Path(clang.package_folder) / "lib" / "clang",
            package_folder / "lib" / "clang",
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
