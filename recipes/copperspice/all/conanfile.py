import os
from os.path import join
from glob import glob
from itertools import chain

from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration


class CopperspiceConanRecipe(ConanFile):
    name = "copperspice"
    description = "CopperSpiceCopperSpice is a set of individual libraries which can be used to develop cross platform software applications in C++"
    license = "LGPL-2.1"
    homepage = "https://www.copperspice.com/"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_gui": [True, False],
        "with_webkit": [True, False]
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_gui": True,
        "with_webkit": False
    }
    requires = (
                "fontconfig/2.13.91",
                "glib/2.65.0",
                "libmysqlclient/8.0.17",
                "openssl/1.1.1d",
                "zlib/1.2.11")
    generators = ["cmake", "cmake_find_package"]
    _cmake = None
    version = "1.6.3"

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def source(self):
        #tools.get(**self.conan_data["sources"][self.version])
        tools.get("https://github.com/copperspice/copperspice/archive/cs-1.6.3.tar.gz")
        os.rename("copperspice-cs-{}".format(self.version), self._source_subfolder)
        tools.replace_in_file(
                os.path.join(self._source_subfolder, "CMakeLists.txt"),
                "project(copperspice)",
        '''project(copperspice)
           include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
           conan_basic_setup()'''
        )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if tools.msvs_toolset(self) == "v140":
            raise ConanInvalidConfiguration("Unsupported Visual Studio Compiler or Toolset")
        minimal_cpp_standard = "17"
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, minimal_cpp_standard)

    def requirements(self):
        if self.options.with_gui:
            self.requires("opengl/system")
            self.requires("xorg/system")
        if self.options.with_webkit:
            self.requires("libxml2/2.9.10")
        if self.settings.os != "Linux":
            self.requires("libiconv/1.16")

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake

        copperspice_config = {
            "WITH_MULTIMEDIA": False,
            "WITH_OPENGL": True,
            "WITH_WEBKIT": self.options.with_webkit,
        }

        self._cmake = CMake(self)
        self._cmake.definitions.update(copperspice_config)
        self._cmake.configure(source_folder=self._source_subfolder)
        return self._cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def _remove_vs_runtime_files(self):
        patterns = [join(self.package_folder, "bin", pattern) for pattern in ["msvcp*.dll", "vcruntime*.dll", "concrt*.dll"]]
        runtime_files = chain.from_iterable(glob(pattern) for pattern in patterns)
        for runtime_file in runtime_files:
            try:
                os.remove(runtime_file)
            except Exception as ex:
                self.output.warn("Could not remove vs runtime file {}, {}".format(runtime_file, ex))

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        self.copy(dst="licenses", src=os.path.join(self._source_subfolder, "licences"))
        #if self.settings.os == "Windows":
        #    self._remove_vs_runtime_files()

        #tools.rmdir(join(self.package_folder, "cmake"))
        #tools.rmdir(join(self.package_folder, "share"))
        #tools.rmdir(join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        semver = tools.Version(self.version)
        #self.cpp_info.includedirs = ["include/pcl-{}.{}".format(semver.major, semver.minor)]
        self.cpp_info.libs = tools.collect_libs(self)
