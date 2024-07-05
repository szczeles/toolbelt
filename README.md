# Set of useful scripts


## Oneliner: Ping host and save the result

    */10 * * * * echo -n `date -R` >> /home/osmc/esp.ping; ping -c 4 192.168.0.105 > /dev/null 2>&1; echo ' ' $? >> /home/osmc/esp.ping


## Sychronize Camera SD card with nas

    rsync -r -a -v -e ssh /media/mario/disk/* nas:/share/CACHEDEV1_DATA/homes/admin/Qsync/sony


## Backup

Elasticsearch (create json files)

    docker run --net=host --rm -ti -v `pwd`/esbackup:/esbackup --entrypoint /usr/local/bin/multielasticdump elasticdump/elasticsearch-dump --match='^.*$' --input=http://localhost:9200 --output=/esbackup --limit 4000

Postgres (to sql and restore)

    pg_dump -U postgres > pv.sql
    cat ~/pv.sql | kubectl exec -ti postgres-85f94bb849-g7rc4 -n pv -- psql -U postgres

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

## Local MQTT

docker run -d -p 1883:1883 --restart always eclipse-mosquitto

## /etc/hosts

```
192.168.0.164   nas
192.168.0.94    smartplug1
192.168.0.220   smartplug2
```
