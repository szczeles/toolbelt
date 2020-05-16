# Set of useful scripts


## Oneliner: Ping host and save the result 

    */10 * * * * echo -n `date -R` >> /home/osmc/esp.ping; ping -c 4 192.168.0.105 > /dev/null 2>&1; echo ' ' $? >> /home/osmc/esp.ping


## Sychronize Camera SD card with nas

    rsync -r -a -v -e ssh /media/mario/disk/* nas:/share/CACHEDEV1_DATA/homes/admin/Qsync/sony

## Links

 * [megatools](https://megous.com/git/megatools)
 * [plowshare](https://github.com/mcrapet/plowshare)
 * [rclone](https://github.com/rclone/rclone)
 * [PosteRazor](https://posterazor.sourceforge.io/) -> splitting images into printable pages

## Issue Let's encrypt cert

    # issue
    sudo mkdir /etc/letsencrypt /var/lib/letsencrypt
    docker run -it --rm -p 80:80 --name certbot \
                -v "/etc/letsencrypt:/etc/letsencrypt" \
                -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
                certbot/certbot:latest certonly \
                --standalone

    # renew
    docker run -it --rm -p 80:80 --name certbot \
                -v "/etc/letsencrypt:/etc/letsencrypt" \
                -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
                certbot/certbot:latest renew
