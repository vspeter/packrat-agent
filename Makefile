all:

install:
	mkdir -p $(DESTDIR)usr/sbin
	mkdir -p $(DESTDIR)etc/packrat
	install -m 755 sbin/repoSync $(DESTDIR)usr/sbin

clean:
	rm -fr build
	dh_clean

test:

lint:

dpkg:
	dpkg-buildpackage -b -us -uc
	dh_clean

dpkg-file:
	@echo $(shell ls ../packrat-agent_*.deb)

.PHONY: all clean test install lint dpkg

