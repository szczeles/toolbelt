# Energa's MojLicznik data scraper

The purpose of this script is to synchronize data available
on Energa's [MojLicznik site](https://mojlicznik.energa-operator.pl/)
with local databases for energy import/export monitoring.

## Usage

First, build the image:

    docker build -t ghcr.io/szczeles/toolbelt/energa-mojlicznik-scraper:0.1 .

Then, schedule it, providing your user credentials for MojLicznik
as secrets:

    kubectl create secret generic -n pv mojlicznik \
        --from-literal=USERNAME=email@domain.com \
        --from-literal=PASSWORD=xxxxx
    kubectl apply -f cronjob.yaml

## Useful queries

#### Invoice verification

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

#### Data completion test

```
with data as (
  select
    cast(ts as date) as d,
    count(*) as samples
  from
    energy
  group by
    1
),
range as (
  select
    generate_series(
      timestamp '2018-12-06', current_date,
      '1 day'
    ):: date AS day
)
select
  *
from
  range
  left join data on data.d = day
where
  data.d is null
  or samples <> 24;
```
