import os
from LocalRepoManager import LocalRepoManager, hashFile


class YUMManager(LocalRepoManager):
    def __init__(self, *args, **kargs):
        super(YUMManager, self).__init__(*args, **kargs)
        self.arch_list = ('x86_86', 'i368')

    def addEntry(self, type, arch, filename, distro, distro_version):
        if type != 'rpm':
            print 'WARNING! New entry not a rpm, skipping...'
            return

    def _writeArchMetadata(self, base_path, arch):
        file_hashes = {}
        dir_path = '%s/%s/repodata' % (base_path, arch)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        full_path = '%s/other.xml'
        wrk = open(full_path, 'w')
        wrk.write('<?xml version="1.0" encoding="UTF-8"?>')
        wrk.close
        (sha1, sha256, md5) = hashFile(full_path)
        file_hashes['other'] = sha1
        """
        <?xml version="1.0" encoding="UTF-8"?>
<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="2">
<package pkgid="bcae9b2fe3443560a3fdfa5cbfc6f759049c6700" name="plato-client-config" arch="noarch"><version epoch="0" ver="0.7" rel="1"/></package>
<package pkgid="215a4f545be3d0edbded791d79a0f2a42a28952d" name="plato-client" arch="x86_64"><version epoch="0" ver="0.25" rel="2"/></package>

</otherdata>
"""
        full_path = '%s/filelists.xml'
        wrk = open(full_path, 'w')
        wrk.write('<?xml version="1.0" encoding="UTF-8"?>')
        wrk.close
        (sha1, sha256, md5) = hashFile(full_path)
        file_hashes['filelists'] = sha1

        full_path = '%s/primary.xml'
        wrk = open(full_path, 'w')
        wrk.write('<?xml version="1.0" encoding="UTF-8"?>')
        wrk.close
        (sha1, sha256, md5) = hashFile(full_path)
        file_hashes['primary'] = sha1
        """
<?xml version="1.0" ?>
<metadata packages="2" xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">


	<package type="rpm">
		<name>plato-client-config</name>
		<arch>noarch</arch>
		<version epoch="0" rel="1" ver="0.7"/>
		<checksum pkgid="YES" type="sha">bcae9b2fe3443560a3fdfa5cbfc6f759049c6700</checksum>
		<summary>Base plato-client config</summary>
		<description>Base plato-client config</description>
		<packager/>
		<url/>
		<time build="1411693942" file="1411679707"/>
		<size archive="8348" installed="5860" package="5642"/>
		<location href="plato-client-config-0.7-1.noarch.rpm"/>
		<format>
			<rpm:license>Nonfree</rpm:license>
			<rpm:vendor/>
			<rpm:group>nonfree/autobots</rpm:group>
			<rpm:buildhost>eth0.centtest.stgr01.iaas-ext.rcsops.com</rpm:buildhost>
			<rpm:sourcerpm>plato-client-config-0.7-1.src.rpm</rpm:sourcerpm>
			<rpm:header-range end="3724" start="880"/>
			<rpm:provides>
				<rpm:entry epoch="0" flags="EQ" name="plato-client-config" rel="1" ver="0.7"/>
			</rpm:provides>
			<rpm:requires>
				<rpm:entry epoch="0" flags="LE" name="rpmlib(PayloadFilesHavePrefix)" rel="1" ver="4.0"/>
				<rpm:entry name="/bin/sh"/>
				<rpm:entry name="plato-client"/>
				<rpm:entry epoch="0" flags="LE" name="rpmlib(CompressedFileNames)" rel="1" ver="3.0.4"/>
			</rpm:requires>
		</format>
	</package>


	<package type="rpm">
		<name>plato-client</name>
		<arch>x86_64</arch>
		<version epoch="0" rel="2" ver="0.25"/>
		<checksum pkgid="YES" type="sha">215a4f545be3d0edbded791d79a0f2a42a28952d</checksum>
		<summary>Base plato-client config</summary>
		<description>Base plato-client config</description>
		<packager/>
		<url/>
		<time build="1411672544" file="1411658664"/>
		<size archive="2203728" installed="2185809" package="803262"/>
		<location href="plato-client-0.25-2.x86_64.rpm"/>
		<format>
			<rpm:license>Nonfree</rpm:license>
			<rpm:vendor/>
			<rpm:group>nonfree/autobots</rpm:group>
			<rpm:buildhost>eth0.centtest.stgr01.iaas-ext.rcsops.com</rpm:buildhost>
			<rpm:sourcerpm>plato-client-0.25-2.src.rpm</rpm:sourcerpm>
			<rpm:header-range end="14848" start="880"/>
			<rpm:provides>
				<rpm:entry name="libdrive.so.2()(64bit)"/>
				<rpm:entry epoch="0" flags="EQ" name="plato-client" rel="2" ver="0.25"/>
				<rpm:entry name="libhardware.so.0()(64bit)"/>
				<rpm:entry epoch="0" flags="EQ" name="plato-client(x86-64)" rel="2" ver="0.25"/>
			</rpm:provides>
			<rpm:requires>
				<rpm:entry name="/usr/bin/python"/>
				<rpm:entry name="libm.so.6()(64bit)"/>
				<rpm:entry name="libc.so.6(GLIBC_2.7)(64bit)"/>
				<rpm:entry epoch="0" flags="EQ" name="python(abi)" ver="2.6"/>
				<rpm:entry name="rtld(GNU_HASH)"/>
				<rpm:entry epoch="0" flags="LE" name="rpmlib(PayloadFilesHavePrefix)" rel="1" ver="4.0"/>
				<rpm:entry name="libm.so.6(GLIBC_2.2.5)(64bit)"/>
				<rpm:entry name="libc.so.6()(64bit)"/>
				<rpm:entry name="libc.so.6(GLIBC_2.2.5)(64bit)"/>
				<rpm:entry name="libc.so.6(GLIBC_2.3)(64bit)"/>
				<rpm:entry name="/bin/sh"/>
				<rpm:entry epoch="0" flags="LE" name="rpmlib(CompressedFileNames)" rel="1" ver="3.0.4"/>
			</rpm:requires>
			<file>/usr/sbin/ldisk</file>
			<file>/usr/sbin/reportDriveStatus</file>
			<file>/usr/sbin/wipedrive</file>
			<file>/usr/sbin/hardwareinfo</file>
			<file>/usr/sbin/reportHardwareStatus</file>
			<file>/usr/sbin/selftest</file>
			<file>/usr/sbin/reportConfigStatus</file>
			<file>/usr/sbin/smartinfo</file>
			<file>/usr/sbin/diskcopy</file>
			<file>/etc/cron.d/plato-client</file>
			<file>/usr/sbin/driveinfo</file>
			<file>/usr/sbin/driveWatcher</file>
			<file>/usr/sbin/configManager</file>
			<file type="dir">/etc/plato</file>
			<file type="dir">/etc/cron.d</file>
		</format>
	</package>


</metadata>
"""


        full_path = '%s/repomd.xml'
        wrk = open(full_path, 'w')
        wrk.write('<?xml version="1.0" encoding="UTF-8"?>')
        wrk.close
        """
        <?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="other_db">
    <location href="repodata/other.sqlite.bz2"/>
    <checksum type="sha">6af0abf1473c84053e1e2b6b9423794dd7b83a87</checksum>
    <timestamp>1411679707</timestamp>
    <open-checksum type="sha">dbf5ec943e38d64f4ebe7a28ad71658e8f6b8d53</open-checksum>
    <database_version>10</database_version>
  </data>
  <data type="other">
    <location href="repodata/other.xml.gz"/>
    <checksum type="sha">70b2913bbe3430d561d1aaef91e2d4d77ed22c93</checksum>
    <timestamp>1411679707</timestamp>
    <open-checksum type="sha">02dbd54adcb92070ef4920c5e7cdddd4f49be5f4</open-checksum>
  </data>
  <data type="filelists_db">
    <location href="repodata/filelists.sqlite.bz2"/>
    <checksum type="sha">d3fa53c968d29f9bd64f81e28a84922389ae3b0b</checksum>
    <timestamp>1411679707</timestamp>
    <open-checksum type="sha">3628241fbcb5fbac0a96409b963eaf648093bf95</open-checksum>
    <database_version>10</database_version>
  </data>
  <data type="filelists">
    <location href="repodata/filelists.xml.gz"/>
    <checksum type="sha">b1d6f64d9aa19ff5153d4732701876c63e15e2b1</checksum>
    <timestamp>1411679707</timestamp>
    <open-checksum type="sha">e51e91bd16a614c8c513ad232f4cc1ec34e715fe</open-checksum>
  </data>
  <data type="primary_db">
    <location href="repodata/primary.sqlite.bz2"/>
    <checksum type="sha">ca6f7f6959d8939ebc084979b419a0ab1164f2f5</checksum>
    <timestamp>1411679708</timestamp>
    <open-checksum type="sha">79d8a0d927564f7467b89e03693535c01bee4760</open-checksum>
    <database_version>10</database_version>
  </data>
  <data type="primary">
    <location href="repodata/primary.xml.gz"/>
    <checksum type="sha">981f205da55c80dcfedbb668ce3a0783cf888f7d</checksum>
    <timestamp>1411679707</timestamp>
    <open-checksum type="sha">21b6a8c2812936050688507e522e25b05473426c</open-checksum>
  </data>
</repomd>
        """

    def writeMetadata(self):
        distro = 'centos'
        distro_verison = 6
        base_path = '%s/%s/%s/%s' % (self.root_dir, distro,
                                     self.component, distro_verison)
        if not os.path.exists(base_path):
            os.makedirs(base_path)

        for arch in self.arch_list:
            for arch in self.arch_list:
                self._writeArchMetadata(base_path, arch)
