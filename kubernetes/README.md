# Kuberetes service setup

Installs:

 * influxdb
 * postgres
 * huawei-solar
 * mojlicznik-scraper
 * grafana
 * whoami service

## Images

    docker build -t geoguess:0.1 .
    docker save geoguess:0.1 | sudo k3s ctr images import -

## Secrets

First, create docker registry creds:

    kubectl create secret -n iot docker-registry ghreg \
        --docker-server=ghcr.io \
        --docker-username=szczeles \
        --docker-password=$CR_PAT \
        --docker-email=szczeles

Then, create a secret for Huawei Fusionsolar and PVOutput:

    kubectl create secret -n iot generic huawei-solar-secret \
        --from-literal=FUSIONSOLAR_USER=$FUSIONSOLAR_USER \
        --from-literal=FUSIONSOLAR_PASSWORD=$FUSIONSOLAR_PASSWORD \
        --from-literal=PVOUTPUT_API_KEY=$PVOUTPUT_API_KEY \
        --from-literal=PVOUTPUT_SYSTEM_ID=$PVOUTPUT_SYSTEM_ID \
        --from-literal=PSQL_URI=$PSQL_URI

Then, a secret for MojLicznik:

    kubectl create secret generic -n iot mojlicznik \
        --from-literal=USERNAME=$MOJLICZNIK_USERNAME \
        --from-literal=PASSWORD=$MOJLICZNIK_PASSWORD \
        --from-literal=PSQL_URI=$PSQL_URI

Then, certs for Mosquitto:

    kubectl create secret tls -n iot mosquitto \
        --cert=mosquitto-server.crt \
        --key=mosquitto-server.key

Secrets for oauth2proxy:

    kubectl create secret generic -n web oauth2proxy \
        --from-literal=OAUTH2_PROXY_CLIENT_ID=$OAUTH2_PROXY_CLIENT_ID \
        --from-literal=OAUTH2_PROXY_CLIENT_SECRET=$OAUTH2_PROXY_CLIENT_SECRET \
        --from-literal=OAUTH2_PROXY_COOKIE_SECRET=$OAUTH2_PROXY_COOKIE_SECRET

Password for ntfy:

    kubectl create secret generic -n web ntfy \
        --from-literal=NTFY_PASSWORD=$NTFY_PASSWORD

GeoGuess:

    kubectl create secret generic -n web geoguess \
        --from-literal=VUE_APP_API_KEY=$VUE_APP_API_KEY \
        --from-literal=VUE_APP_FIREBASE_API_KEY=$VUE_APP_FIREBASE_API_KEY \
        --from-literal=VUE_APP_FIREBASE_PROJECT_ID=$VUE_APP_FIREBASE_PROJECT_ID \
        --from-literal=VUE_APP_FIREBASE_MESSAGING_SENDER_ID=$VUE_APP_FIREBASE_MESSAGING_SENDER_ID \
        --from-literal=VUE_APP_FIREBASE_APP_ID=$VUE_APP_FIREBASE_APP_ID \
        --from-literal=VUE_APP_FIREBASE_AUTH_DOMAIN=$VUE_APP_FIREBASE_AUTH_DOMAIN \
        --from-literal=VUE_APP_FIREBASE_DATABASE_URL=$VUE_APP_FIREBASE_DATABASE_URL \
        --from-literal=VUE_APP_STORAGE_BUCKET=$VUE_APP_STORAGE_BUCKET

## Manifests

MQTT, influx, postgres, huawei, energa:

    $ kubectl apply -f iot.yaml

Cert-manager:

    $ kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml

Grafana, oauth2proxy, whoami, ntfy:

    $ kubectl apply -f web.yaml

## Backup

Local volumes backup in S3:

    3 19 * * * bash -l -c 'tar cfz /tmp/volumes-backup.tar.gz /var/lib/rancher/k3s/storage/ && /usr/local/bin/aws s3 cp /tmp/volumes-backup.tar.gz s3://mariusz-mlops-backup/' > /tmp/backup.log 2>&1
