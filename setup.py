#!/usr/bin/env python3

import glob
from distutils.core import setup
from distutils.command.build_py import build_py
from setuptools import find_packages
import os

class custom_build( build_py ):
    def run( self ):
      # get .pys
      for package in self.packages:  # derived from build_py.run
        package_dir = self.get_package_dir(package)
        modules = self.find_package_modules(package, package_dir)
        for (package_, module, module_file) in modules:
          assert package == package_
          if os.path.basename( module_file ).endswith( '_test.py' ) or os.path.basename( module_file ) == 'tests.py':
            continue
          self.build_module(module, module_file, package)

setup( name='packrat-agent',
       version='0.1',
       description='Packrat Agent',
       author='Peter Howe',
       author_email='peter.howe@emc.com',
       packages=[ 'packratAgent' ],
       cmdclass={ 'build_py': custom_build }
     )

