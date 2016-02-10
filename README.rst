=============================
packrat-agent
=============================

consumes packrat to build repos

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


This will list our newly created key, there are two parts to the key the Private key (labeld with (sub)), this is what is used to sign the repo, do not let this key
out of your control, and keep it backed up, otherwise re-keying all the subscribers to the repo will be painfull.  The other key is the Public Key (labeld with (pub)).
edit /etc/packrat/mirror.conf and enter the hash ( ie: 6F9893FE ) as the gpg_sign_key.  Now export the public key::

  gpg --armor --output /var/www/repo-key --export < the pub ie: B2CAFB61 >

the path `/var/www/repo-key` should be where http clients can get to and download it, it is recomened to put it in the root of the http root directory.  Now we can
force a sync and make sure we get what we expect.

  repoSync
 
you should get something like::

  Last Sync was from None to None
  Processing Repos....  
  Processing repo "APT - Production"
    Writing Metadata...
  Processing repo "YUM - Production"
    Writing Metadata...
  Done!

you are all set
