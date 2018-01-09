all:

install:
	mkdir -p $(DESTDIR)usr/sbin
	mkdir -p $(DESTDIR)etc/packrat
	install -m 755 sbin/packrat-agent $(DESTDIR)usr/sbin

clean:
	$(RM) -fr build
	$(RM) -f dpkg

full-clean: clean
	dh_clean

test-distros:
	echo xenial

test-requires:
	echo python3 python3-dateutil python3-pip python3-pytest python3-pytest-cov

test-setup:
	pip3 --proxy=http://192.168.200.53:3128 install cinp
	pip3 install -e .

test:
	py.test-3 -x --cov=packratAgent --cov-report html --cov-report term  -vv packratAgent

dpkg-distros:
	echo xenial

dpkg-requires:
	echo dpkg-dev debhelper cdbs python3-dev python3-setuptools

dpkg:
	dpkg-buildpackage -b -us -uc
	touch dpkg

dpkg-file:
	@echo $(shell ls ../packrat-agent_*.deb):trusty

.PHONY: all install clean dpkg-distros dpkg-requires dpkg-file
