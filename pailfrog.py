#!/usr/bin/env python3
"""Pailfrog - Amazon S3 bucket investigation tool."""
from datetime import datetime
import os
import socket
import sys
import xml.etree.ElementTree as ET

from ipaddress import ip_address, ip_network
import requests


# an empty list to contain all the S3 IPV4 ranges.
s3List = []
# an empty list to contain all the IP addresses which are in the S3 IPV4 range.
result_list = []

IPV4_IDENT_STRING = "\"ip_prefix\": \""
IPV6_IDENT_STRING = "\"ipv6_prefix\": \""
IP_TAIL_STRING = "\","
TARGET_URL_TEMPLATE = "http://{domain}.s3.amazonaws.com"


def main(test_domain):
    """Run the bucket investigation tool."""

    # This would be better as an argument, e.g. --update-ranges
    do_amazon_test = "junkdata"
    while do_amazon_test not in ('y', 'Y', 'n', 'N'):
        do_amazon_test = input("Update Amazon IP ranges? Y/N ")
        if do_amazon_test == 'y' or 'Y':
            print("Retrieving updated Amazon IP ranges...")
            update_amazon_ips()
            print("Ranges updated successfully.")
        elif do_amazon_test == 'n' or 'N':
            print("Skipping Amazon range update")

    print("Testing hostname: '" + test_domain + "'.")
    target_url = TARGET_URL_TEMPLATE.format(domain=test_domain)
    print('S3 bucket for {domain} is at {target}'.format(
        domain=test_domain,
        target=target_url,
    ))
    current_ip_address = socket.gethostbyname(target_url)
    print("IP address of host is: " + current_ip_address)

    with open("./config/sourceIPv4ranges.csv", "r") as source_ips_handle:
        source_ips = source_ips_handle.readlines()

    bucket_in_valid_s3_range = False
    for line in source_ips:
        current_range = ip_network(line.strip())
        if ip_address(current_ip_address) in current_range:
            print('Bucket found in s3 range {s3_range}'.format(
                s3_range=str(current_range),
            ))
            bucket_in_valid_s3_range = True
            break

    if bucket_in_valid_s3_range:
        response = requests.get(target_url)

        print('Response for {target} is: {status}'.format(
            target=target_url,
            status=response.status_code,
        ))

        if response.status_code == 200:
            print("S3 root directory is publicly listable. Enumerating files.")
            harvest_root(target_url, response.content)
    else:
        sys.stderr.write(
            'Bucket IP {ip} was not found in any known s3 ranges.\n'.format(
                ip=str(current_ip_address),
            )
        )
        sys.exit(1)


def range_date_check():
    """Check how long since the amazon IP ranges were last updated."""
    if os.path.isfile("./config/source_ips.json"):
        file_modified_on = os.path.getmtime("./config/source_ips.json")
        print("File updated on: " + str(file_modified_on))
        current_time = datetime.now()
        print("Current time: " + str(current_time))
        temp_time = current_time - file_modified_on
        print("Diff is: " + str(temp_time))
        if (current_time - file_modified_on) > 86400:
            update_amazon_ips()
        else:
            print("Amazon IP addresses up to date. Skipping update.")


def update_amazon_ips():
    """Check the current S3 IP addresses are known."""
    response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json")
    with open("./config/source_ips.json", "wb") as output_handle:
        output_handle.write(response.json())
    # TODO: If we really want to be dealing with CSV we should just pass it
    # on from here and then return the parsed data, to be written by whatever
    # called it. Avoiding mixing I/O into random functions that aren't named
    # in an obvious way to indicate they will write it will make this harder
    # to maintain later
    parse_amazon_ips()


def parse_amazon_ips():
    """Parse the updated amazon IPs into CSV (why?)"""
    # TODO: Note that this should be CIDR notation IPv4/6 ranges
    # TODO: De-duplicate entries
    # TODO: Only use s3 ranges
    # open both IPv4 and IPv6 files in replacement mode#
    # TODO: No, don't, use a context manager around just the code writing them
    ipv4_file = open("./config/sourceIPv4ranges.csv", "w")
    ipv6_file = open("./config/sourceIPv6ranges.csv", "w")
    # open the source_ips.json file in read-only mode#
    source_ips = open("./config/sourceIPs.json", "r")

    for line in source_ips:
        if IPV4_IDENT_STRING in line:
            temp_line = line.replace(IPV4_IDENT_STRING, "")
            final_string = temp_line.replace(IP_TAIL_STRING, ",")
            ipv4_file.write(final_string.strip() + "\n")
        elif IPV6_IDENT_STRING in line:
            temp_line = line.replace(IPV6_IDENT_STRING, "")
            final_string = temp_line.replace(IP_TAIL_STRING, ",")
            ipv6_file.write(final_string.strip() + "\n")

    # TODO: If doing this without a context manager, it's best to open in a
    # try block and close with a finally
    # (but really, just use the context manager)
    ipv4_file.close()
    ipv6_file.close()
    source_ips.close()


# function to read and parse the XML file returned when and
# list and enumerate all files within it
# parameters passed are:
#    s3_bucket_in        - the response contents of the S3 root request.
def harvest_root(target_url, s3_bucket_in):
    """Enumerate all files found in the bucket for the domain.
    :param bucket: Bucket ID to check.
    :param domain: Domain under which the bucket resides.
    """
    # TODO: FIX PARSING ERROR HERE #
    s3_tree = ET.fromstring(s3_bucket_in)
    print(str(s3_tree))
    file_list = s3_tree.findall("Contents")
    print(str(file_list))
    print(str(len(file_list)) + " files found")
    for keys in file_list:
        file_name = keys.find("Key").text
        print("Attempting to download " + file_name)
        file_string = target_url + "/" + file_name
        file_contents = requests.get(file_string)
        if file_contents.status_code == 200:
            print('Writing to ./files/' + file_name)
            with open(file_name, 'wb') as file_harvester:
                file_harvester.write(file_contents.content)
        elif file_contents.status_code == 403:
            print(file_name + "status code 403: permission denied.")
        elif file_contents.status_code == 404:
            print(file_name + "status code 404: file not found.")


if __name__ == "__main__":
    # We could do better here, but for a first pass let's just work with one
    # domain and introduce proper argument parsing when we need it.
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: {} <domain to test>\n'.format(sys.argv[0]))
        sys.exit(1)
    main(sys.argv[1])
