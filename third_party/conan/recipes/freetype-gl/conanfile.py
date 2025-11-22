from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import copy, load, replace_in_file
from conan.tools.scm import Git
import os


class FreetypeglConan(ConanFile):
    name = "freetype-gl"
    version = "79b03d9.1"
    _git_commit = "79b03d9"  # Git commit to checkout
    license = "BSD-2-Clause"
    description = "freetype-gl is a small library for displaying Unicode in OpenGL"
    topics = ("freetype", "opengl", "unicode", "fonts")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC" : [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeDeps"
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        self.requires("glad/0.1.34")
        self.requires("freetype/2.10.4")
        self.requires("zlib/1.2.11")

    def source(self):
        from conan.tools.files import patch
        git = Git(self)
        # In Conan 2.x, source_folder is pre-created with exports_sources
        # Clone to a subdirectory
        src_path = os.path.join(self.source_folder, "src")
        git.clone(url="https://github.com/rougier/freetype-gl.git", target=src_path)
        git.folder = src_path
        git.checkout(commit=self._git_commit)
        # Apply patches if they exist using Conan 2.x patch tool
        patch_file = os.path.join(self.recipe_folder, "patches", "001-patch.diff")
        if os.path.exists(patch_file):
            patch(self, base_path=src_path, patch_file=patch_file, strip=1)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["freetype-gl_WITH_GLAD"] = True
        tc.variables["freetype-gl_WITH_GLEW"] = False
        tc.variables["freetype-gl_USE_VAO"] = False
        tc.variables["freetype-gl_BUILD_DEMOS"] = False
        tc.variables["freetype-gl_BUILD_APIDOC"] = False
        tc.variables["freetype-gl_BUILD_HARFBUZZ"] = False
        tc.variables["freetype-gl_BUILD_MAKEFONT"] = False
        tc.variables["freetype-gl_BUILD_TESTS"] = False
        
        # Add dependency include directories for legacy CMakeLists.txt
        include_dirs = []
        lib_dirs = []
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                include_dirs.append(incdir)
            for libdir in dep.cpp_info.libdirs:
                lib_dirs.append(libdir)
        
        if include_dirs:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_dirs)
            # Also add as compiler flags for legacy CMakeLists.txt
            include_flags = " ".join([f"-I{d}" for d in include_dirs])
            tc.variables["CMAKE_C_FLAGS"] = include_flags
            tc.variables["CMAKE_CXX_FLAGS"] = include_flags
        
        if lib_dirs:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src"))
        cmake.build()

    def package(self):
        from conan.tools.files import get
        import shutil
        
        # Copy the library manually instead of using cmake.install() which creates broken symlinks
        # The library is built in the build folder
        build_lib = os.path.join(self.build_folder, "libfreetype-gl.a")
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        if os.path.exists(build_lib):
            shutil.copy2(build_lib, os.path.join(lib_dir, "libfreetype-gl.a"))
        
        # Copy headers manually to ensure real files, not symlinks
        # Copy to include/freetype-gl/ to match the include paths in the code
        # Copy root headers - use excludes to skip symlinks and harfbuzz directory
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, "src"), 
             dst=os.path.join(self.package_folder, "include", "freetype-gl"), 
             keep_path=False,
             excludes=["harfbuzz/*"])
        
        # Copy headers from demos subdirectory (contains mat4.h)
        copy(self, "*.h", 
             src=os.path.join(self.source_folder, "src", "demos"), 
             dst=os.path.join(self.package_folder, "include", "freetype-gl"), 
             keep_path=False)
        
        # Copy fonts and shaders
        copy(self, "*", 
             src=os.path.join(self.source_folder, "src", "fonts"), 
             dst=os.path.join(self.package_folder, "fonts"))
        copy(self, "*", 
             src=os.path.join(self.source_folder, "src", "shaders"), 
             dst=os.path.join(self.package_folder, "shaders"))
        
    def package_info(self):
        self.cpp_info.libs = ["freetype-gl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["fonts", "shaders"]
