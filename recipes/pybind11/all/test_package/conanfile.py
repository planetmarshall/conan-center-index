from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv
from conan.tools.build import can_run
from conan.tools.layout import cmake_layout

import os
import sys


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    win_bash = True

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["PYTHON_EXECUTABLE"] = self._python_interpreter
        toolchain.generate()

        run = VirtualRunEnv(self)
        run.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _python_interpreter(self):
        if getattr(sys, "frozen", False):
            return "python"
        return sys.executable

    def test(self):
        if can_run(self):
            python_path = os.path.join(self.build_folder, self.cpp.build.libdirs[0])
            module_path = os.path.join(self.source_folder, "test.py")
            self.run(f"PYTHONPATH={python_path} {self._python_interpreter} {module_path}", env="conanrun")
