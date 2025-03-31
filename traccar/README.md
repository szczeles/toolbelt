# Traccar server

## Setup

    helm repo add traccar https://traccar.github.io/traccar-helm/
    helm upgrade --install my-traccar traccar/traccar -n traccar -f values.yaml --create-namespace
    kubectl patch -n traccar svc/external-my-traccar -p="{\"spec\": {\"externalIPs\": [\"$(curl -s ifconfig.me)\"]}}"

## IMEIs

* Tracker 1: `867946050695259`
