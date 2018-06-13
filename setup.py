#!/usr/bin/env python3

import os
from distutils.core import setup
from distutils.command.build_py import build_py


class build( build_py ):
  def run( self ):
    # get .pys
    for package in self.packages:  # derived from build_py.run
      package_dir = self.get_package_dir( package )
      modules = self.find_package_modules( package, package_dir )
      for ( package2, module, module_file ) in modules:
        assert package == package2
        if os.path.basename( module_file ).endswith( '_test.py' ) or os.path.basename( module_file ) == 'tests.py':
          continue
        self.build_module( module, module_file, package )

setup( name='packrat-agent',
       version='0.9',
       description='Packrat Agent',
       author='Peter Howe',
       author_email='peter.howe@emc.com',
       packages=[ 'packratAgent', 'packratAgent/yum' ],
       cmdclass={ 'build_py': build }
       )
