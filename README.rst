=============================
packrat-agent
=============================

consumes packrat to build repos


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
