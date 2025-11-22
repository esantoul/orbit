from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.files import get, patch, replace_in_file, copy, load, save, rmdir, chdir, collect_libs
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration

from collections import defaultdict
import json
import re
import os.path
import os


class LLVMCoreConan(ConanFile):
    name = 'llvm-core'
    version = '12.0.0'
    description = (
        'A toolkit for the construction of highly optimized compilers,'
        'optimizers, and runtime environments.'
    )
    license = 'Apache-2.0 WITH LLVM-exception'
    topics = ('conan', 'llvm')
    homepage = 'https://github.com/llvm/llvm-project/tree/master/llvm'
    url = 'https://github.com/conan-io/conan-center-index'

    settings = ('os', 'arch', 'compiler', 'build_type')
    options = {
        'shared': [True, False],
        'fPIC': [True, False],
        'components': [None, 'ANY'],
        'targets': [None, 'ANY'],
        'exceptions': [True, False],
        'rtti': [True, False],
        'threads': [True, False],
        'lto': ['On', 'Off', 'Full', 'Thin'],
        'static_stdlib': [True, False],
        'unwind_tables': [True, False],
        'expensive_checks': [True, False],
        'use_perf': [True, False],
        'use_sanitizer': [
            'Address',
            'Memory',
            'MemoryWithOrigins',
            'Undefined',
            'Thread',
            'DataFlow',
            'Address;Undefined',
            'None'
        ],
        'with_ffi': [True, False],
        'with_zlib': [True, False],
        'with_xml2': [True, False]
    }
    default_options = {
        'shared': False,
        'fPIC': True,
        'components': 'all',
        'targets': 'all',
        'exceptions': True,
        'rtti': True,
        'threads': True,
        'lto': 'Off',
        'static_stdlib': False,
        'unwind_tables': True,
        'expensive_checks': False,
        'use_perf': False,
        'use_sanitizer': 'None',
        'with_ffi': False,
        'with_zlib': True,
        'with_xml2': True
    }

    exports_sources = ['patches/*']
    generators = ['CMakeDeps']
    no_copy_source = True

    @property
    def _source_subfolder(self):
        return 'source'

    def layout(self):
        cmake_layout(self)

    def _supports_compiler(self):
        compiler = str(self.settings.compiler)
        version = Version(self.settings.compiler.version)
        major_rev = int(str(version.major))
        minor_rev = int(str(version.minor)) if version.minor and str(version.minor) != 'None' else 0

        unsupported_combinations = [
            [compiler == 'gcc', major_rev == 5, minor_rev < 1],
            [compiler == 'gcc', major_rev < 5],
            [compiler == 'clang', major_rev < 4],
            [compiler == 'apple-clang', major_rev < 9],
            [compiler == 'Visual Studio', major_rev < 15]
        ]
        if any(all(combination) for combination in unsupported_combinations):
            message = 'unsupported compiler: "{}", version "{}"'
            raise ConanInvalidConfiguration(message.format(compiler, version))

    def _patch_sources(self):
        for p in self.conan_data.get('patches', {}).get(self.version, []):
            patch(self, **p)

    def _patch_build(self):
        if os.path.exists('FindIconv.cmake'):
            replace_in_file(self, 'FindIconv.cmake', 'iconv charset', 'iconv')

    @property
    def _zlib_library_name(self):
        # The library's filename is different on Windows
        return self.dependencies["zlib"].cpp_info.libs[0]

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC
            del self.options.with_xml2

    def build_requirements(self):
        self.tool_requires('cmake/3.27.9')  # Updated for conan-center availability

    def requirements(self):
        if self.options.with_ffi:
            self.requires('libffi/3.3')
        if self.options.get_safe('with_zlib', False):
            self.requires('zlib/1.2.11')
        if self.options.get_safe('with_xml2', False):
            self.requires('libxml2/2.9.10')

    def validate(self):
        if self.options.shared:  # Shared builds disabled just due to the CI
            message = 'Shared builds not currently supported'
            raise ConanInvalidConfiguration(message)
        if self.options.exceptions and not self.options.rtti:
            message = 'Cannot enable exceptions without rtti support'
            raise ConanInvalidConfiguration(message)
        self._supports_compiler()

    def source(self):
        get(self, **self.conan_data['sources'][self.version], strip_root=True, destination=self._source_subfolder)
        self._patch_sources()

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables['BUILD_SHARED_LIBS'] = False
        tc.variables['CMAKE_SKIP_RPATH'] = True
        tc.variables['CMAKE_POSITION_INDEPENDENT_CODE'] = \
            self.options.get_safe('fPIC', default=False) or self.options.shared

        if not self.options.shared:
            tc.variables['DISABLE_LLVM_LINK_LLVM_DYLIB'] = True

        tc.variables['LLVM_TARGET_ARCH'] = 'host'
        tc.variables['LLVM_TARGETS_TO_BUILD'] = str(self.options.targets)
        tc.variables['LLVM_BUILD_LLVM_DYLIB'] = self.options.shared
        tc.variables['LLVM_DYLIB_COMPONENTS'] = str(self.options.components)
        tc.variables['LLVM_ENABLE_PIC'] = \
            self.options.get_safe('fPIC', default=False)

        if self.settings.compiler == 'Visual Studio':
            build_type = str(self.settings.build_type).upper()
            tc.variables['LLVM_USE_CRT_{}'.format(build_type)] = \
                str(self.settings.compiler.runtime)

        tc.variables['LLVM_ABI_BREAKING_CHECKS'] = 'WITH_ASSERTS'
        tc.variables['LLVM_ENABLE_WARNINGS'] = True
        tc.variables['LLVM_ENABLE_PEDANTIC'] = True
        tc.variables['LLVM_ENABLE_WERROR'] = False

        tc.variables['LLVM_TEMPORARILY_ALLOW_OLD_TOOLCHAIN'] = True
        tc.variables['LLVM_USE_RELATIVE_PATHS_IN_DEBUG_INFO'] = False
        tc.variables['LLVM_BUILD_INSTRUMENTED_COVERAGE'] = False
        tc.variables['LLVM_OPTIMIZED_TABLEGEN'] = True
        tc.variables['LLVM_REVERSE_ITERATION'] = False
        tc.variables['LLVM_ENABLE_BINDINGS'] = False
        tc.variables['LLVM_CCACHE_BUILD'] = False

        tc.variables['LLVM_INCLUDE_TOOLS'] = self.options.shared
        tc.variables['LLVM_INCLUDE_EXAMPLES'] = False
        tc.variables['LLVM_INCLUDE_TESTS'] = False
        tc.variables['LLVM_INCLUDE_BENCHMARKS'] = False
        tc.variables['LLVM_APPEND_VC_REV'] = False
        tc.variables['LLVM_BUILD_DOCS'] = False
        tc.variables['LLVM_ENABLE_IDE'] = False
        tc.variables['LLVM_ENABLE_TERMINFO'] = False

        tc.variables['LLVM_ENABLE_EH'] = self.options.exceptions
        tc.variables['LLVM_ENABLE_RTTI'] = self.options.rtti
        tc.variables['LLVM_ENABLE_THREADS'] = self.options.threads
        tc.variables['LLVM_ENABLE_LTO'] = str(self.options.lto)
        tc.variables['LLVM_STATIC_LINK_CXX_STDLIB'] = \
            self.options.static_stdlib
        tc.variables['LLVM_ENABLE_UNWIND_TABLES'] = \
            self.options.unwind_tables
        tc.variables['LLVM_ENABLE_EXPENSIVE_CHECKS'] = \
            self.options.expensive_checks
        tc.variables['LLVM_ENABLE_ASSERTIONS'] = \
            self.settings.build_type == 'Debug'

        tc.variables['LLVM_USE_NEWPM'] = False
        tc.variables['LLVM_USE_OPROFILE'] = False
        tc.variables['LLVM_USE_PERF'] = self.options.use_perf
        if self.options.use_sanitizer == 'None':
            tc.variables['LLVM_USE_SANITIZER'] = ''
        else:
            tc.variables['LLVM_USE_SANITIZER'] = \
                str(self.options.use_sanitizer)

        tc.variables['LLVM_ENABLE_Z3_SOLVER'] = False
        tc.variables['LLVM_ENABLE_LIBPFM'] = False
        tc.variables['LLVM_ENABLE_LIBEDIT'] = False
        tc.variables['LLVM_ENABLE_FFI'] = self.options.with_ffi
        tc.variables['LLVM_ENABLE_ZLIB'] = \
            'FORCE_ON' if self.options.get_safe('with_zlib', False) else False
        tc.variables['LLVM_ENABLE_LIBXML2'] = \
            self.options.get_safe('with_xml2', False)
        tc.generate()

    def build(self):
        self._patch_build()
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, self._source_subfolder))
        cmake.build()

    def package(self):
        copy(self, 'LICENSE.TXT', src=os.path.join(self.source_folder, self._source_subfolder), dst=os.path.join(self.package_folder, 'licenses'))
        lib_path = os.path.join(self.package_folder, 'lib')

        cmake = CMake(self)
        cmake.install()

        if not self.options.shared:
            for ext in ['.a', '.lib']:
                lib = '**/lib/*LLVMTableGenGlobalISel{}'.format(ext)
                copy(self, lib, src=self.build_folder, dst=os.path.join(self.package_folder, 'lib'), keep_path=False)
                lib = '*LLVMTableGenGlobalISel{}'.format(ext)
                copy(self, lib, src=os.path.join(self.build_folder, 'lib'), dst=os.path.join(self.package_folder, 'lib'))

            self.run('cmake --graphviz=graph/llvm.dot .')
            with chdir(self, 'graph'):
                dot_text = load(self, 'llvm.dot').replace('\r\n', '\n')

            dep_regex = re.compile(r'//\s(.+)\s->\s(.+)$', re.MULTILINE)
            deps = re.findall(dep_regex, dot_text)

            dummy_targets = defaultdict(list)
            for target, dep in deps:
                if not target.startswith('LLVM'):
                    dummy_targets[target].append(dep)

            cmake_targets = {
                'libffi::libffi': 'ffi',
                'ZLIB::ZLIB': self._zlib_library_name,
                'Iconv::Iconv': 'iconv',
                'LibXml2::LibXml2': 'xml2'
            }

            components = defaultdict(list)
            for lib, dep in deps:
                if not lib.startswith('LLVM'):
                    continue
                elif dep.startswith('-delayload:'):
                    continue
                elif dep.startswith('LLVM'):
                    components[dep]
                elif dep in cmake_targets:
                    dep = cmake_targets[dep]
                elif os.path.exists(dep):
                    dep = os.path.splitext(os.path.basename(dep))[0]
                    dep = dep.replace('lib', '')
                dep = dep.replace('-l', '')

                if dep in dummy_targets.keys():
                    components[lib].extend(dummy_targets[dep])
                    components[lib] = list(set(components[lib]))
                else:
                    components[lib].append(dep)

        rmdir(self, os.path.join(self.package_folder, 'bin'))
        rmdir(self, os.path.join(self.package_folder, 'lib', 'cmake'))
        rmdir(self, os.path.join(self.package_folder, 'share'))

        for name in os.listdir(lib_path):
            if 'LLVM' not in name:
                os.remove(os.path.join(lib_path, name))

        if not self.options.shared:
            if self.options.get_safe('with_zlib', False):
                if not self._zlib_library_name in components['LLVMSupport']:
                    components['LLVMSupport'].append(self._zlib_library_name)
            components_path = \
                os.path.join(self.package_folder, 'lib', 'components.json')
            with open(components_path, 'w') as components_file:
                json.dump(components, components_file, indent=4)
        else:
            suffixes = ['.dylib', '.so']
            for name in os.listdir(lib_path):
                if not any(suffix in name for suffix in suffixes):
                    os.remove(os.path.join(lib_path, name))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = collect_libs(self)
            if self.settings.os == 'Linux':
                self.cpp_info.system_libs = ['pthread', 'rt', 'dl', 'm']
            elif self.settings.os == 'Macos':
                self.cpp_info.system_libs = ['m']
            return

        components_path = \
            os.path.join(self.package_folder, 'lib', 'components.json')
        with open(components_path, 'r') as components_file:
            components = json.load(components_file)

        dependencies = ['ffi', self._zlib_library_name, 'iconv', 'xml2']
        targets = {
            'ffi': 'libffi::libffi',
            self._zlib_library_name: 'zlib::zlib',
            'xml2': 'libxml2::libxml2'
        }

        for lib, deps in components.items():
            component = lib[4:].replace('LLVM', '').lower()

            self.cpp_info.components[component].libs = [lib]

            self.cpp_info.components[component].requires = [
                dep[4:].replace('LLVM', '').lower()
                for dep in deps if dep.startswith('LLVM')
            ]
            for lib, target in targets.items():
                if lib in deps:
                    self.cpp_info.components[component].requires.append(target)

            self.cpp_info.components[component].system_libs = [
                dep for dep in deps
                if not dep.startswith('LLVM') and dep not in dependencies
            ]
