all:

install:
	mkdir -p $(DESTDIR)usr/sbin
	mkdir -p $(DESTDIR)etc/packrat
	install -m 755 sbin/repoSync $(DESTDIR)usr/sbin

clean:
	$(RM) -fr build
	$(RM) -f dpkg

full-clean: clean
	dh_clean

dpkg-distros:
	echo trusty

dpkg-requires:
	echo dpkg-dev debhelper cdbs python-dev python-setuptools

dpkg:
	dpkg-buildpackage -b -us -uc
	touch dpkg

dpkg-file:
	@echo $(shell ls ../packrat-agent_*.deb)

.PHONY: all install clean dpkg-distros dpkg-requires dpkg-file
