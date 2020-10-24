# Kuberetes setup for huawei-solar

Installs:

 * influxdb
 * postgres
 * huawei-solar

## Setup

First, create docker registry creds:

    kubectl create secret -n pv docker-registry ghreg \
        --docker-server=docker.pkg.github.com \
        --docker-username=... \
        --docker-password=... \
        --docker-email=...

Then, create a secret for Huawei Fusionsolar and PVOutput:

    kubectl create secret -n pv generic huawei-solar-secret \
        --from-literal=FUSIONSOLAR_USER=... \
        --from-literal=FUSIONSOLAR_PASSWORD=... \
        --from-literal=PVOUTPUT_API_KEY=... \
        --from-literal=PVOUTPUT_SYSTEM_ID=...

And apply manifest:

    kubectl apply -f k8s.yaml
