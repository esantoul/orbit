from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.files import get, replace_in_file
from conan.errors import ConanInvalidConfiguration
import os
import time
import platform


class grpcConan(ConanFile):
    name = "grpc_codegen"
    version = "1.27.3"
    description = "Google's RPC library and framework."
    topics = ("conan", "grpc", "rpc")
    url = "https://github.com/inexorgame/conan-grpc"
    homepage = "https://github.com/grpc/grpc"
    license = "Apache-2.0"
    exports_sources = ["CMakeLists.txt"]
    generators = "CMakeDeps"
    short_paths = True  # Otherwise some folders go out of the 260 chars path length scope rapidly (on windows)

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }
    package_type = "application"  # This is a build tool

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("abseil/20211102.0")
        self.requires("c-ares/1.25.0")
        self.requires("openssl/1.1.1w")  # Updated for Conan 2.x
        self.requires("protobuf/3.21.12")  # Updated for Conan 2.x - 3.9.1 not available
        self.requires("zlib/1.2.11")

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            compiler_version = int(str(self.settings.compiler.version))
            if compiler_version < 14:
                raise ConanInvalidConfiguration("gRPC can only be built with Visual Studio 2015 or higher.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])
        extracted_dir = "grpc-" + self.version
        if platform.system() == "Windows":
            time.sleep(8) # Work-around, see https://github.com/conan-io/conan/issues/5205
        os.rename(extracted_dir, self._source_subfolder)
        
        # In Conan 2.x, CMakeDeps creates proper absl:: targets, so no patching needed

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables['gRPC_BUILD_CODEGEN'] = "ON"
        tc.variables['gRPC_BUILD_CSHARP_EXT'] = "OFF"
        tc.variables['gRPC_BUILD_TESTS'] = "OFF"
        tc.variables['gRPC_INSTALL'] = "OFF"
        # Only build the C++ plugin
        tc.variables["gRPC_BUILD_GRPC_CPP_PLUGIN"] = "ON"
        tc.variables["gRPC_BUILD_GRPC_CSHARP_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_NODE_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_PHP_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_PYTHON_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_RUBY_PLUGIN"] = "OFF"
        tc.variables['gRPC_CARES_PROVIDER'] = "package"
        tc.variables['gRPC_ZLIB_PROVIDER'] = "package"
        tc.variables['gRPC_SSL_PROVIDER'] = "package"
        tc.variables['gRPC_PROTOBUF_PROVIDER'] = "none"
        tc.variables['gRPC_ABSL_PROVIDER'] = "none"
        tc.variables['gRPC_GFLAGS_PROVIDER'] = "none"
        tc.variables['gRPC_BENCHMARK_PROVIDER'] = "none"
        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            tc.variables["CMAKE_CXX_FLAGS"] = "-D_WIN32_WINNT=0x600"
            tc.variables["CMAKE_C_FLAGS"] = "-D_WIN32_WINNT=0x600"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        from conan.tools.files import copy
        import glob
        copy(self, pattern="LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Search recursively for grpc_cpp_plugin in the build folder
        plugin_pattern = os.path.join(self.build_folder, "**/grpc_cpp_plugin")
        plugins = glob.glob(plugin_pattern, recursive=True)
        if plugins:
            plugin_dir = os.path.dirname(plugins[0])
            self.output.info(f"Found grpc_cpp_plugin at {plugins[0]}")
            copy(self, "grpc_cpp_plugin*", src=plugin_dir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        else:
            self.output.warn(f"grpc_cpp_plugin not found in build folder: {self.build_folder}")

    def package_info(self):
        # Conan 2.x: Use buildenv_info to expose tools to consumers
        bin_path = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = [bin_path]
        # For build context (when used as build_requires)
        self.buildenv_info.prepend_path("PATH", bin_path)
        # Also set an environment variable with the explicit path
        grpc_plugin = os.path.join(bin_path, "grpc_cpp_plugin")
        self.buildenv_info.define("GRPC_CPP_PLUGIN", grpc_plugin)

