from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get, patch, copy, load, save, replace_in_file
import os


class LibunwindstackAndroidDependenciesConan(ConanFile):
    name = "libunwindstack-android-dependencies"
    version = "20210709"
    license = "MIT"
    author = "Henning Becker <henning.becker@gmail.com>"
    homepage = "https://android.googlesource.com/platform/system/libbase/"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    exports_sources = ["CMakeLists.txt", "cmake/FindFilesystem.cmake", "patches/*"]
    options = {"fPIC" : [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # lzma_sdk provides 7zCrc.h, Xz.h, XzCrc64.h headers needed by libunwindstack
        self.requires("lzma_sdk/19.00@orbitdeps/stable")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        for source in self.conan_data["sources"][self.version]:
            get(self, **source)
        for p in self.conan_data.get("patches", {}).get(self.version, []):
            patch(self, **p)
        # Note: We use the CMakeLists.txt from exports_sources, not from source

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        license_path = os.path.join(self.package_folder, "LICENSE")
        license_content = []
        for license in self.conan_data.get("license_files", {}).get(self.version, []):
            license_content.append("================================================================================\n")
            license_content.append("Name: {}\n".format(license["library_name"]))
            license_content.append("URL: {}\n\n".format(license.get("library_url", "")))
            license_content.append(load(self, os.path.join(self.source_folder, license["src"])))
            license_content.append("\n\n")
        save(self, license_path, "".join(license_content))

        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        # List the actual libraries that are built and installed
        # Don't include "lib" prefix - CMake adds it automatically
        self.cpp_info.libs = ["log_static", "procinfo", "base"]
        # lzma_sdk headers are propagated as a transitive dependency
