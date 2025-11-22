from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.files import get, replace_in_file, copy
from conan.errors import ConanInvalidConfiguration
import os
import shutil
import time
import platform


class grpcConan(ConanFile):
    name = "grpc"
    version = "1.27.3"
    description = "Google's RPC library and framework."
    topics = ("conan", "grpc", "rpc")
    url = "https://github.com/inexorgame/conan-grpc"
    homepage = "https://github.com/grpc/grpc"
    license = "Apache-2.0"
    exports_sources = ["CMakeLists.txt", "gRPCTargets-helpers.cmake"]
    generators = "CMakeDeps"
    short_paths = True  # Otherwise some folders go out of the 260 chars path length scope rapidly (on windows)

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def requirements(self):
        self.requires("abseil/20211102.0")
        self.requires("zlib/1.2.11")
        self.requires("openssl/1.1.1w")  # Updated for Conan 2.x
        self.requires("protobuf/3.21.12")  # Updated for Conan 2.x - 3.9.1 not available
        self.requires("c-ares/1.25.0")

    def build_requirements(self):
        # protoc is included in protobuf package from conan-center
        # self.build_requires("protoc_installer/3.9.1@bincrafters/stable")

        if self.user and self.channel:
            self.build_requires("grpc_codegen/{}@{}/{}".format(self.version, self.user, self.channel))
        else:
            self.build_requires("grpc_codegen/{}".format(self.version))

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            del self.options.fPIC
            compiler_version = int(str(self.settings.compiler.version))
            if compiler_version < 14:
                raise ConanInvalidConfiguration("gRPC can only be built with Visual Studio 2015 or higher.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version])
        extracted_dir = "grpc-" + self.version
        if platform.system() == "Windows":
            time.sleep(8) # Work-around, see https://github.com/conan-io/conan/issues/5205
        os.rename(extracted_dir, self._source_subfolder)

        # In Conan 2.x, CMakeDeps creates proper absl:: targets
        # No patching needed - we'll build only specific targets

    def generate(self):
        from conan.tools.cmake import CMakeToolchain
        from conan.tools.env import VirtualBuildEnv
        import glob
        
        # Generate build environment with build requirements (including grpc_codegen)
        env = VirtualBuildEnv(self)
        env.generate()
        
        # Conan 2.x: Variables are now set in generate()
        tc = CMakeToolchain(self)
        tc.variables['gRPC_BUILD_CODEGEN'] = "OFF"  # Don't build plugin, we use grpc_codegen  
        tc.variables['gRPC_BUILD_CSHARP_EXT'] = "OFF"
        tc.variables['gRPC_BUILD_TESTS'] = "OFF"
        tc.variables['gRPC_INSTALL'] = "ON"
        tc.variables["gRPC_BUILD_GRPC_CPP_PLUGIN"] = "OFF"
        # Disable optional targets that need grpc_cpp_plugin
        tc.variables["gRPC_BUILD_GRPC_CPP_PLUGIN"] = "OFF"
        
        # Find grpc_cpp_plugin from build requirements
        # In Conan 2.x, use direct_build to access build requirements
        for dep in self.dependencies.direct_build.values():
            if dep.ref.name == "grpc_codegen":
                # Search for grpc_cpp_plugin in the package bin folders
                bin_paths = dep.cpp_info.bindirs
                for bin_path in bin_paths:
                    plugin_candidates = glob.glob(os.path.join(bin_path, "grpc_cpp_plugin*"))
                    if plugin_candidates:
                        tc.variables["_gRPC_CPP_PLUGIN"] = plugin_candidates[0]
                        self.output.info(f"Found grpc_cpp_plugin at: {plugin_candidates[0]}")
                        break
        tc.variables["gRPC_BUILD_GRPC_CSHARP_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_PHP_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_PYTHON_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_RUBY_PLUGIN"] = "OFF"
        tc.variables["gRPC_BUILD_GRPC_NODE_PLUGIN"] = "OFF"
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
        # Build only core targets, not optional ones that need grpc_cpp_plugin
        cmake.build(target="grpc")
        cmake.build(target="grpc++")
        cmake.build(target="grpc_unsecure")
        cmake.build(target="grpc++_unsecure")
        cmake.build(target="grpc_cronet")
        cmake.build(target="grpc_plugin_support")
        cmake.build(target="grpc++_alts")

    def package(self):
        cmake = CMake(self)
        cmake.install()

        shutil.rmtree(os.path.join(self.package_folder, "lib", "pkgconfig"))
        shutil.rmtree(os.path.join(self.package_folder, "lib", "cmake", "grpc", "modules"))

        copy(self, "gRPCTargets-helpers.cmake", src=self.source_folder, dst=os.path.join(self.package_folder, "lib", "cmake", "grpc"))
        copy(self, "LICENSE*", src=os.path.join(self.source_folder, self._source_subfolder), dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Conan 2.x: Only include libraries that were actually built
        self.cpp_info.libs = [
            "grpc++_alts",
            "grpc++_unsecure",
            "grpc++",
            "grpc_unsecure",
            "grpc_plugin_support",
            "grpc_cronet",
            "grpc",
            "gpr",
            "address_sorting",
            "upb",
        ]


        if self.settings.compiler == "Visual Studio":
            self.cpp_info.system_libs += ["wsock32", "ws2_32"]

