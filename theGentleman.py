import configparser
import json
import logging
import sys
from mitmproxy import io
from mitmproxy.exceptions import FlowReadException
from os import write
from urllib import parse


config = configparser.ConfigParser()
config.read('./config.ini')

def get_headers(request) -> str:
    headers = [f"{header}:{request.headers[header]}\\n" for header in request.headers]
    headers_string = ''.join(headers)
    return f'"{headers_string}"'

def get_data(request) -> str:
    data_str = request.content.decode('utf-8')
    data_dict = json.loads(data_str)
    data = parse.urlencode(data_dict).encode().decode()
    return data

def mount_post_and_put_cmd(request) -> str:
    data = get_data(request)
    url = f'{request.scheme}://{request.host}{request.path}'
    headers = get_headers(request)
    sqlmap_cmd = f"{config['setup']['sqlmap_path']} --batch --random-agent -u \"{url}\" --method={request.method} --headers={headers} --data='{data}'"
    return sqlmap_cmd

def mount_get_requests(request) -> str:
    url = f'{request.scheme}://{request.host}{request.path}'
    headers = get_headers(request)
    sqlmap_cmd = f"{config['setup']['sqlmap_path']} --batch --random-agent -u \"{url}\" --headers={headers}"
    return sqlmap_cmd

def get_sqlmap_cmds(log_file) -> list():
    requests = []
    for f in log_file.stream():
        for _ in f.request.headers:
            if f.request.method == "GET":
                requests.append(mount_get_requests(f.request))
            if f.request.method == ("PUT" or "POST"):
                requests.append(mount_post_and_put_cmd(f.request))
    return requests

def main():
    with open(sys.argv[1], "rb") as logfile:
        freader = io.FlowReader(logfile)
        try:
            print('Mouting sqlmap commands...')
            cmds = get_sqlmap_cmds(freader)
            with open(f'run-sqli', 'w') as script:
                script.write(f"#!/bin/bash\n")
                for request in set(cmds):
                    script.write(f"{request}\n")
            print('Done!')
        except FlowReadException as e:
            print(f"Flow file corrupted: {e}")

if __name__ == "__main__":
    main()