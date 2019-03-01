VERSION := $(shell head -n 1 debian/changelog | awk '{match( $$0, /\(.+?\)/); print substr( $$0, RSTART+1, RLENGTH-2 ) }' | cut -d- -f1 )

all:
	./setup.py build

install:
	mkdir -p $(DESTDIR)/usr/bin
	mkdir -p $(DESTDIR)/etc/packrat
	mkdir -p $(DESTDIR)/etc/apache2/sites-available

	install -m 755 bin/packrat-agent $(DESTDIR)/usr/bin
	install -m 644 mirror.conf.sample $(DESTDIR)/etc/packrat/mirror.conf
	install -m 644 apache.conf $(DESTDIR)/etc/apache2/sites-available/repo.conf

	./setup.py install --root $(DESTDIR) --install-purelib=/usr/lib/python3/dist-packages/ --prefix=/usr --no-compile -O0

version:
	echo $(VERSION)

clean:
	./setup.py clean
	$(RM) -fr build
	$(RM) -f dpkg
	dh_clean || true

dist-clean: clean

.PHONY:: all install clean dist-clean

test-distros:
	echo ubuntu-xenial

test-requires:
	echo flake8 python3 python3-dateutil python3-pip python3-pytest python3-pytest-cov python3-cinp

lint:
	flake8 --ignore=E501,E201,E202,E111,E126,E114,E402,W605 --statistics .

test:
	py.test-3 -x --cov=packratAgent --cov-report html --cov-report term  -vv packratAgent

.PHONY:: test-distrostest-requires lint test

dpkg-distros:
	echo ubuntu-xenial

dpkg-requires:
	echo dpkg-dev debhelper cdbs python3-dev python3-setuptools

dpkg:
	dpkg-buildpackage -b -us -uc
	touch dpkg

dpkg-file:
	@echo $(shell ls ../packrat-agent_*.deb):xenial

.PHONY:: dpkg-distros dpkg-requires dpkg-file
