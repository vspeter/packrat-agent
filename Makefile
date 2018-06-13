all:
	./setup.py build

install:
	mkdir -p $(DESTDIR)/usr/sbin
	mkdir -p $(DESTDIR)/etc/packrat
	mkdir -p $(DESTDIR)/etc/apache2/sites-available

	install -m 755 sbin/packrat-agent $(DESTDIR)/usr/sbin
	install -m 644 mirror.conf.sample $(DESTDIR)/etc/packrat/mirror.conf
	install -m 644 apache.conf $(DESTDIR)/etc/apache2/sites-available/repo.conf

	./setup.py install --root $(DESTDIR) --install-purelib=/usr/lib/python3/dist-packages/ --prefix=/usr --no-compile -O0

clean:
	./setup.py clean
	$(RM) -fr build
	$(RM) -f dpkg

full-clean: clean
	dh_clean

test-distros:
	echo xenial

test-requires:
	echo python3 python3-dateutil python3-pip python3-pytest python3-pytest-cov python3-cinp

test-setup:
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
