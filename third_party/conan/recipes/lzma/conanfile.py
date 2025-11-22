from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get, copy
import os


class LzmasdkConan(ConanFile):
    name = "lzma_sdk"
    version = "19.00"
    license = "MIT"
    author = "Henning Becker <henning.becker@gmail.com>"
    homepage = "https://www.7-zip.org/sdk.html"
    description = "The LZMA SDK provides the documentation, samples, header files, libraries, and tools you need to develop applications that use LZMA compression."
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    exports_sources = "CMakeLists.txt", "conandata.yml"
    options = {"fPIC" : [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        cmake_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        from conan.tools.files import download
        # Download 7z file
        lzma_path = os.path.join(self.source_folder, "lzma.7z")
        download(self, self.conan_data["sources"][self.version]["url"],
                 lzma_path, sha256=self.conan_data["sources"][self.version]["sha256"])
        # Extract using CMake's tar command which supports 7z
        lzma_dir = os.path.join(self.source_folder, "lzma")
        os.mkdir(lzma_dir)
        # Change to lzma directory and extract
        self.run(f"cd {lzma_dir} && cmake -E tar x {lzma_path}")
        os.remove(lzma_path)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "lzma/C"), 
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*lzma_sdk.lib", src=self.build_folder, 
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pdb", src=self.build_folder, 
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=self.build_folder, 
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["lzma_sdk"]
        self.cpp_info.defines = ["_7ZIP_ST"]

