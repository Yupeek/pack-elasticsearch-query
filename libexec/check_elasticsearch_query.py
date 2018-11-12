#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import json


import sys
import urllib.parse

try:
    import requests
    from jq import jq
except ImportError as e:
    import os
    pip = os.path.join(os.path.dirname(sys.executable), os.path.basename(sys.executable).replace('python', 'pip'))
    print('UNKNOWN - %s. please install it via pip. try  "pip install %s" or "%s install %s"' % (e, e.name, pip, e.name))
    sys.exit(3)


def parse_args(argv):
    """
    parse the command line arguments

    >>> parse_args('-q *'.split(' '))
    {'url': 'https://localhost:9200/_search', 'query': '*', 'data': '', 'range': ('@timestamp', 'now-2h'), 'warn': 'false', 'crit': 'false'}

    :param argv:
    :return:
    """
    # -H $_HOSTESQ_HOST$ --port $_HOSTESQ_PORT$ --url $_HOSTESQ_URL$ --query $_HOSTESQ_QUERY$
    # --range $_HOSTESQ_RANGE$ -w $_HOSTESQ_WARN$ -c $_HOSTESQ_CRIT$ --data $_HOSTESQ_DATA$
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', default='localhost')
    parser.add_argument('-p', '--port', default="9200")
    parser.add_argument('-u', '--url', default='/_search')
    parser.add_argument('-s', '--secure', default=False)
    parser.add_argument('--cred', default='')
    parser.add_argument('-q', '--query', required=True)
    parser.add_argument('-d', '--data', default='')
    parser.add_argument('-r', '--range', default='now-2h')
    parser.add_argument('-w', '--warning', default='false')
    parser.add_argument('-c', '--critical', default='false')
    args = parser.parse_args(argv)

    if args.cred:
        cred = args.cred + '@'
    else:
        cred = ''

    url = urllib.parse.urlunsplit((
        "https" if args.secure else "http",
        "%s%s:%s" % (
            cred,
            args.host,
            args.port,
        ),
        args.url,
        '', ''
    ))
    if '=' in args.range:
        range_field, range_date = args.range.split('=')
    else:
        range_field, range_date = "@timestamp", args.range
    try:
        return {
            "url": url,
            "query": args.query,
            "data": jq(args.data),
            "range": (range_field, range_date),
            "warn": jq(args.warning),
            "crit": jq(args.critical),
            "data_text": args.data,
            "warn_text": args.warning,
            "crit_text": args.critical,
        }
    except ValueError as ve:
        print('UNKNOWN - error while parsing jq expression: %s.' % (ve))
        sys.exit(3)


def build_query(args):
    if args['query'].startswith('{'):
        query = json.loads(args['query'])

    else:
        query = {"query": {
            "bool": {
              "must": [
                {"query_string": {
                  "default_field": "message",
                  "query": args['query']
                }}
              ],
            }
        }}
    range_field, range_value = args['range']
    if range_value:
        if "query" not in query:
            query['query'] = {}
        if 'bool' not in query['query']:
            query['query']['bool'] = {}
        if 'filter' not in query['query']['bool']:
            query['query']['bool']['filter'] = []
        query['query']['bool']['filter'].append({
            "range": {range_field: {
                "gte": range_value
        }}})
    return query


def format_data(data):
    return ' '.join('%s=%s' % (k, v) for k, v in data.items())


def main(argv):
    args = parse_args(argv[1:])
    query = build_query(args)

    try:
        res = requests.get(args['url'], data=json.dumps(query), headers={'content-type': 'application/json'})
    except Exception as e:
        print('UNKNOWN - error while qerying the service %s' % (e,))
        return 3
    if res.status_code >= 400:
        print('UNKNOWN - elasticsearch responded [%s] %s' % (res.status_code, res.text))
        return 3
    try:
        esdata = res.json()
    except Exception as e:
        print('UNKNOWN - error while qerying the service %s' % e)
        return 3
    if args['crit'].transform(esdata):
        status = 'CRITICAL - [Triggered by %s]' % args['crit_text'], 2
    elif args['warn'].transform(esdata):
        status = 'WARNING - [Triggered by %s]' % args['warn_text'], 1
    else:
        status = 'OK', 0

    try:
        data = args['data'].transform(esdata)

    except Exception as e:
        txt_data = "error while formating data: %s" % (repr(e), )
        formated_data = ""
    else:
        txt_data = json.dumps(data)
        formated_data = format_data(data)

    print('%s - %s|%s' % (status[0], txt_data, formated_data))
    return status[1]


if __name__ == '__main__':
    sys.exit(main(sys.argv))
