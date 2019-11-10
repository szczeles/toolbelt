# Set of useful scripts


## Oneliner: Ping host and save the result 

    */10 * * * * echo -n `date -R` >> /home/osmc/esp.ping; ping -c 4 192.168.0.105 > /dev/null 2>&1; echo ' ' $? >> /home/osmc/esp.ping


## Sychronize Camera SD card with nas

    rsync -r -a -v -e ssh /media/mario/disk/* nas:/share/CACHEDEV1_DATA/homes/admin/Qsync/sony

## Links

 * [megatools](https://megous.com/git/megatools)
 * [plowshare](https://github.com/mcrapet/plowshare)
 * [rclone](https://github.com/rclone/rclone)
