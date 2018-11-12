pack-elasticsearch-query
========================

Shinken configuration pack for check based on value stored in
elasticsearch

this pack allow to retreive datas from elasticsearch via /\_search and
raise alert based on his result.

you provide a query, and the expected values from critical/warn and this
check will do the rest.

quick start
-----------

sample of a check which just search if there is logs from our server:

    define host{
       name           my-verbose-host
       address        192.168.0.25
       use            elasticsearch-query
       register       0

    }

this default config will check if our server logged something in ES
since the last hour

this other exemple will check if the latest value of a specific field
(app.extra.nb\_published) in ES is always \> 1400:

    define host{
       name           my-publisher-host
       address        ...
       use            elasticsearch-query
       
       _ESQ_HOST $HOSTADDRESS$
       _ESQ_PORT 9200
       _ESQ_URL  /_search
       _ESQ_CREDENTIALS
       _ESQ_QUERY  {"_source":["@timestamp","app.extra.nb_published"],"size":1,"sort":[{"@timestamp":{"order":"desc"}}],"query":{"bool":{"must":[{"match":{"source.environment":"prod"}},{"match":{"source.service_name":"joboffer_algolia_publisher"}},{"exists":{"field":"app.extra.nb_published"}}]}}}
       _ESQ_RANGE now-2h
       _ESQ_WARN .hits.total>0 and .hits.hits[]._source.app.extra.nb_published < 1400
       _ESQ_CRIT .hits.total>0 and .hits.hits[]._source.app.extra.nb_published < 500
       _ESQ_DATA {logs: .hits.total, published: (.hits.hits[0]._source.app.extra.nb_published // 0)}
       
    }

see
<https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html>
to write the \_ESQ\_QUERY part

multiple query, multiple service/host
-------------------------------------

to make multiple query for a given host, you can add more services to your host.

    define host {
    
      name my-host
      use  generic-host
      
      _ESQ_HOST my-es-server.lan
      _ESQ_PORT 9200
      _ESQ_URL  /_search
      
    }
    
    define service{
       use            elasticsearch-query
       service_description           check_maiev_logs
       register       1
       host_name      my-host
       
       _ESQ_QUERY source.project: "yupeek/maiev" AND source.environment: prod
       _ESQ_RANGE now-1h
       _ESQ_WARN .hits.total<10
       _ESQ_CRIT .hits.total<1
       _ESQ_DATA {logs: .hits.total}
    }
    
    
    define service{
       use            elasticsearch-query
       service_description           check_other_logs
       register       1
       host_name      my-host
       
       _ESQ_QUERY source.project: "yupeek/other" AND source.environment: prod
       _ESQ_RANGE now-1h
       _ESQ_WARN .hits.total<10
       _ESQ_CRIT .hits.total<1
       _ESQ_DATA {logs: .hits.total}
    }


this will create the host without default check, but will add 2 services which both will make a distinct query to elasticsearch.


requirements
------------

this pack require python2 or 3, with packages `jq` and `requests` :

    pip install jq requests

configuration
-------------

you can customize the check with the folowing host variable

-   `_ESQ_HOST`: the host of the elasticsearch server
-   `_ESQ_PORT`: the port of elasticsearch
-   `_ESQ_URL`: the url to query to make the search. by default will
    search throug all index via /\_search
-   `_ESQ_CREDENTIALS`: the username:password part to connect to
    elasticsearch
-   `_ESQ_QUERY`: the query to send to elasticsearch to retreive the
    data to check.
-   `_ESQ_RANGE`: the range in which the logs should be retreived. see
    the RANGE section for more info
-   `_ESQ_WARN`: a jq expression returning a boolean to raise WARNING
    status (see CHECK section)
-   `_ESQ_CRIT`: a jq expression returning a boolean to raise CRITICAL
    status (see CHECK section)
-   `_ESQ_DATA`: a jq expression returning a dict with the metrics you
    whant to return to display in shinken

### \_ESQ\_QUERY

the query can be either a valid [DSL
query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
or a [query
string](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html).

### \_ESQ\_RANGE

this parameter allow to specify a relative range to inject in the query.
ie : `now-1h` will add in the \_ESQ\_QUERY a filter about the date
range.

this value is passed directly to elasticsearch, see [elasticsearch
documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-range-query.html)
for more informations.

if this field is not empty, the resulting query sent to elasticsearch
will contains
`.query.bool.filter.range.<fieldname>.gte = <computed_date>`

### CHECK

the config \_ESQ\_CRIT and \_ESQ\_WARN accept a valid [jq
expression](https://stedolan.github.io/jq/manual/)

-   `_ESQ_CRIT` and `_ESQ_WARN` must return a boolean. the default check
    `.hits.total>0` do just that.

\* `_ESQ_DATA` must return a dict with the metrics you whant to display
in shinken. it's easier to understant why a check has failed if you add
the matching metrics in `_ESQ_DATA`.
