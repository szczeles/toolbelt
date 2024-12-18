# Kuberetes service setup

Installs:

 * influxdb
 * postgres
 * huawei-solar
 * mojlicznik-scraper
 * grafana
 * whoami service

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
        --from-literal=PVOUTPUT_SYSTEM_ID=$PVOUTPUT_SYSTEM_ID

Then, a secret for MojLiczni:

    kubectl create secret generic -n iot mojlicznik \
        --from-literal=USERNAME=$MOJLICZNIK_USERNAME \
        --from-literal=PASSWORD=$MOJLICZNIK_PASSWORD

Then, certs for Mosquitto:

    kubectl create secret tls -n iot mosquitto \
        --cert=mosquitto-server.crt \
        --key=mosquitto-server.key

Secrets for oauth2proxy:

    kubectl create secret generic -n web oauth2proxy \
        --from-literal=OAUTH2_PROXY_CLIENT_ID=$OAUTH2_PROXY_CLIENT_ID \
        --from-literal=OAUTH2_PROXY_CLIENT_SECRET=$OAUTH2_PROXY_CLIENT_SECRET \
        --from-literal=OAUTH2_PROXY_COOKIE_SECRET=$OAUTH2_PROXY_COOKIE_SECRET

## Manifests

MQTT, influx, postgres, huawei, energa:

    $ kubectl apply -f iot.yaml

Cert-manager:

    $ kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml

Grafana, oauth2proxy, whoami:

    $ kubectl apply -f web.yaml

## Backup

Local volumes backup in S3:

    3 19 * * * bash -l -c 'tar cfz /tmp/volumes-backup.tar.gz /var/lib/rancher/k3s/storage/ && /usr/local/bin/aws s3 cp /tmp/volumes-backup.tar.gz s3://mariusz-mlops-backup/' > /tmp/backup.log 2>&1
