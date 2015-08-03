=============================
packrat-agent
=============================

consumes packrat to build repos

Setting up Apache
-----------------

aptitude install apache2
a2dissite 000-default

mkdir /var/www/repo


/etc/apache2/sites-available/repo.conf 

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

a2ensite repo

/etc/init.d/apache2 restart

Setting up Signing
------------------

gpg --gen-key
 - 1 - RSA and RSA
 - (pick a key size) (2048)
 - (pick expiration length) (0)
 - real name = repo.< DOMAIN >
 - no email
 - no comment
 - Confirm
 - no password

gpg --list-keys
private key (sub) -> signwith
public key (pub) -> export


put the sub signature (something like 01725BB8) in /etc/packrat/mirror.conf under gpg_sign_key

export the public key and put it someplace where it can be retrieved

gpg --armor --output /var/www/repo-key --export < the pub ie: 0FD29E45 >
