=============================
packrat-agent
=============================

Consumes packrat to build on disk repos.

Before you Begin
----------------

You will need to have a working packrat before setting up the agent.  See the packrat documentation.
It is ok to run the agent on the same server as the packrat server, just make sure the http web server
config can handle the virtual hosting correctly.  Also make sure the agent and the packrat server
are not overlapping in the filesystem.

The Agent will maintain long running HTTP server to the packrat server to enable it to be triggerd
when relavant changes are needed, thus avoiding having to poll at regular intervals.  The agent will still
do a full scan of the local filesystem and a clean pull from packrat every depending on the full_sync_interval
setting (in seconds).  Any file in root_dir that is either not a file maintained by the agent or in the keep_file
list will be removed during the full sync scan.

Configuration File
==================

The Agent is configured with the /etc/packrat/mirror.conf file.  All information not contained in this file is
maintained on the packrat server.  If you sign your repo/packages with packrat-agent, make sure to keep a backup
of your encryption keys, this information is not stored on the packrat server.

example configuration::

  [packrat]
  host: packrat.myco.com
  name: prod
  psk: prod_psk
  proxy: http://proxy.inside.myco.com:3128/

  [mirror]
  description: prod-mirror
  root_dir: /var/www/repo
  gpg_sign_key: B2CAFB61
  state_db: /var/lib/packratAgent/state.db
  full_sync_interval: 900
  keep_file_list: /var/www/repo/repo-key

packrat section
---------------

host: hostname information of the packrat server

name: this mirror's name on the packrat server

psk: this mirror's psk on the packrat server

proxy: http proxy if needed to get to the packrat server

mirror section
--------------

description: depending on the repo type, this is used as the description of the mirror, embeded in the repo metadata

root_dir: the root directory to place the configured repos into

gpg_sign_key: key to sign repo metadata and packages with, see signing section below

state_db: path to the sqlite internal state dat base, the agent will create and maintain this file.  If this file is deleted
the agent may remove local package files while getting re-synced with the packrat server

full_sync_interval: the interval between full scans of the local filesystem and full state checks with the packrat server.  NOTE:
the file system can can take quite a while depending on the speed of the underlying storage system and the size of the repos.  Each
package file's hash is checked aginst the packrat server, and also evaluated to see if it should exist at all.  If inconsistancies
are found the packages in question are removed and re-downloaded, this may case windows where the repo metadata does
not match the packages on disk.  This value will probably need to be tuned to balance the need of enforcing consistancy with
the packrat server and potential inconsintanies on disk.  In normal operations local filesystem changes should not happen, but
this check is there incase it does.

keep_file: a file that is not generated/maintained by the agent that you do not want cleaned up during the filesystem scan.  Commonly
used to keep the published public keep from getting cleaned up.  Add a keep_file entry with the full path of each file you want
the agent to leave.


Setting up Agent
================

These instructions will use Apache as the HTTP server.  Apache is not required, but is used here as an example.  For the most part
any HTTP server that can serve from the local filesystem will work.  This example allows for directory browsing via HTTP, this
is not required, but is very helpfull when troubleshooting.

If you allready have the a HTTP server to serve your repo, skip to the repo signing section.

Setting up Apache
-----------------

For our example we will use Apache to server the repos, however any HTTP server can be used.  First install and configure apache::

  aptitude install apache2
  a2dissite 000-default

  mkdir /var/www/repo

create /etc/apache2/sites-available/repo.conf with the following::

  <VirtualHost *:80>
    ServerName repo
    ServerAlias repo.<domain>

    DocumentRoot /var/www/repo

    <Directory /var/www/repo/>
        Options Indexes FollowSymLinks MultiViews
        AllowOverride None
        Order allow,deny
        allow from all
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/repo_error.log
    CustomLog ${APACHE_LOG_DIR}/repo_access.log combined
  </VirtualHost>


Enable the repo Site::

  a2ensite repo
  /etc/init.d/apache2 restart


Next edit /etc/packrat/mirror.conf, set the host to the master packrat server, set the name and psk to the name and psk in the mirror entry on packrat,
if you need to use a proxy to get to the master packrat server, put that in.  If you did not use /var/www/repo as your http root directory, set root_dir
to you http root directory.


Setting up Signing
------------------

If you would like to have your repo signed::

  gpg --gen-key

These Answers to the questions go with the example apache config, modify as needed::

 - 1 - RSA and RSA
 - (pick a key size) (2048)
 - (pick expiration length) (0)
 - real name = repo.< DOMAIN >
 - no email
 - no comment
 - Confirm
 - no password

Now we need to get the key where we can use it::

  gpg --list-keys

for example::

  /root/.gnupg/pubring.gpg
  ------------------------
  pub   2048R/B2CAFB61 2016-02-10
  uid                  repo.test
  sub   2048R/6F9893FE 2016-02-10


This will list our newly created key, there are two parts to the key the Subkey (labeld with (sub)), this is what is used to sign the repo.  The other key is the Public Key (labeld with (pub)).
edit /etc/packrat/mirror.conf and enter the hash ( ie: 6F9893FE ) as the gpg_sign_key.  NOTE: there is also a Private key (viewed with another option).  For more information about GPG and how
the keys interact and their use see http://www.gnupg.org.  If you intend for your public key to be trusted long term or enfoce package security with signatures, you will want to export and store
the Master Key Pair, see the gpnupg site for details on that. Now export the public key::

  gpg --armor --output /var/www/repo/repo-key --export < the pub ie: B2CAFB61 >

the path `/var/www/repo-key` should be where http clients can get to and download it, it is recomened to put it in the root of the http root directory.

restart repoSyc/packratAgent you should now see messages like ::

  INFO:root:apt: Signing distro precise
  INFO:root:apt: Signing distro trusty
  INFO:root:apt: Signing distro xenial

in your logs.


NOTE:

newer versions of gpg don't show they subkey fingerprint by default, add `--with-subkey-fingerprints` to show them::

  $ gpg --list-keys --with-subkey-fingerprints
  /root/.gnupg/pubring.kbx
  ------------------------------
  pub   rsa3072 2018-06-13 [SC] [expires: 2020-06-12]
        8BFE3D3D3945F40B1FDF16E06662EFCFB2B63C30
  uid           [ultimate] testing
  sub   rsa3072 2018-06-13 [E] [expires: 2020-06-12]
        AC418843B048A55266269920B94271513106BFA6
