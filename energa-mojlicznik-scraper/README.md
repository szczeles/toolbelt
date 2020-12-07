# Energa's MojLicznik data scraper

The purpose of this script is to synchronize data available
on Energa's [MojLicznik site](https://mojlicznik.energa-operator.pl/)
with local databases for energy import/export monitoring.

## Usage

First, build the image:

    docker build -t energa-mojlicznik-scraper .

Then, run it, providing your user credentials for MojLicznik
and databases urls.

    docker run -d energa-mojlicznik-scraper \
        --mojlicznik-user email@domain.com \
        --mojlicznik-password xxxxx \
        [--postgres-url postgres://user:pass@host/db] \
        [--influxdb-url http://host:8086]
