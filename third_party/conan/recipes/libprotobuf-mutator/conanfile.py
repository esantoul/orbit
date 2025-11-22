from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, replace_in_file
import os


class LibprotobufMutatorConan(ConanFile):
    name = "libprotobuf-mutator"
    version = "20200506"
    license = "Apache-2.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    # protoc is included in protobuf package from conan-center
    options = { "fPIC" : [True, False] }
    default_options = { "fPIC" : True }
    short_paths = True

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"][self.version])
        # Modify CMakeLists.txt for Conan 2.x
        cmakelists = os.path.join(self.source_folder, self.conan_data["source_subfolder"][self.version], "CMakeLists.txt")
        
        # Replace find_package() calls to use CONFIG mode with modern targets
        replace_in_file(self, cmakelists,
            "find_package(LibLZMA)",
            "find_package(LibLZMA REQUIRED CONFIG)")
        replace_in_file(self, cmakelists,
            "include_directories(${LIBLZMA_INCLUDE_DIRS})",
            "# Using modern CMake targets, no include_directories needed")
        
        replace_in_file(self, cmakelists,
            "find_package(ZLIB)",
            "find_package(ZLIB REQUIRED CONFIG)\nset(ZLIB_LIBRARIES ZLIB::ZLIB)")
        replace_in_file(self, cmakelists,
            "include_directories(${ZLIB_INCLUDE_DIRS})",
            "# Using modern CMake targets, no include_directories needed")
        
        replace_in_file(self, cmakelists,
            "  find_package(Protobuf REQUIRED)",
            "  find_package(protobuf REQUIRED CONFIG)\n  set(PROTOBUF_LIBRARIES protobuf::libprotobuf)")
        replace_in_file(self, cmakelists,
            "  include_directories(${PROTOBUF_INCLUDE_DIRS})",
            "  # Using modern CMake targets, no include_directories needed")

    def requirements(self):
        self.requires("xz_utils/5.4.5")  # Modern LZMA from conan-center
        self.requires("zlib/1.2.11")
        self.requires("protobuf/3.21.12")  # Updated for Conan 2.x

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LIB_PROTO_MUTATOR_TESTING"] = False
        tc.variables["CMAKE_CXX_FLAGS"] = "-fPIE"
        tc.variables["CMAKE_C_FLAGS"] = "-fPIE"
        tc.generate()

    def build(self):
        self._source_subfolder = self.conan_data["source_subfolder"][self.version]
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, self._source_subfolder))
        cmake.build()

    def package(self):
        self._source_subfolder = self.conan_data["source_subfolder"][self.version]
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, self._source_subfolder, "src"), 
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, self._source_subfolder, "port"), 
             dst=os.path.join(self.package_folder, "include", "port"))
        copy(self, "*.lib", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pdb", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["protobuf-mutator-libfuzzer", "protobuf-mutator"]
