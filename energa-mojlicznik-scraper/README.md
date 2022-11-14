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

## Useful queries

Invoice verification:

```
select 
  sum(imported) as energia_pobrana, 
  sum(exported) as energia_oddana, 
  sum(
    case when imported - exported > 0 then imported - exported else 0 end
  ) as sum_sald_dodatnich, 
  sum(
    case when imported - exported < 0 then exported - imported else 0 end
  ) as sum_sald_ujemnych 
from 
  energy 
where 
  ts between (
    timestamp '2022-09-01 00:00:00' at time zone 'Europe/Warsaw'
  ) 
  and (
    timestamp '2022-10-31 23:00:00' at time zone 'Europe/Warsaw'
  );
```
