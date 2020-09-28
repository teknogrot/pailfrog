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
resultList = []

ipv4IdentString = "\"ip_prefix\": \""
ipv6IdentString = "\"ipv6_prefix\": \""
ipAddressTailString = "\","
httpString = "http://"
S3BucketString = ".s3.amazonaws.com"
keyLineStartString = "<Key>"
keyLineEndString = "</Key>"


def main(test_domain):
    """Run the bucket investigation tool."""
    doAmazonTest = "junkdata"

    while doAmazonTest not in ('y', 'Y', 'n', 'N'):
        doAmazonTest = input("Update Amazon IP ranges? Y/N ")
        if doAmazonTest == 'y' or 'Y':
            print("Retrieving updated Amazon IP ranges...")
            updateAmazonIPs()
            print("Ranges updated successfully.")
        elif doAmazonTest == 'n' or 'N':
            print("Skipping Amazon range update")

    print("Testing hostname: '" + test_domain + "'.")
    current_ip_address = socket.gethostbyname(test_domain)
    print("IP address of host is: " + current_ip_address)

    # open sourceIPv4ranges.csv in read-only mode.
    sourceIPs = open("./config/sourceIPv4ranges.csv", "r")
    for line in sourceIPs:
        current_range = ip_network(line.strip())
        if ip_address(current_ip_address) in current_range:
            resultList.append("Domain: \"" + test_domain + "\" is hosted in Amazon S3 at: " + current_ip_address + "\n")
    sourceIPs.close()

    # print out the domains which successfully resolved and check if the root is accessible.
    for item in resultList:
        print (item)
        s3Root = checkS3Root(test_domain)
        httpCode = s3Root.status_code
        if httpCode == 200:
            print("HTTP response for " + httpString + test_domain + S3BucketString + " is: " + str(httpCode))
            print("S3 root directory is publicly listable. Enumerating files.")
            harvestRoot(s3Root.content, test_domain)
        else:
            print("HTTP response for " + httpString + test_domain + S3BucketString + " is: " + str(httpCode))
    sys.exit(0)


def rangeDateCheck():
    """Check how long since the amazon IP ranges were last updated."""
    if os.path.isfile("./config/sourceIPs.json"):
        fileModifiedOn = os.path.getmtime("./config/sourceIPs.json")
        print("File updated on: " + str(fileModifiedOn))
        currentTime = datetime.now()
        print("Current time: " + str(currentTime))
        tempTime = currentTime - fileModifiedOn
        print("Diff is: " + str(tempTime))
        if (currentTime - fileModifiedOn) > 86400:
            updateAmazonIPs()
        else:
            print("Amazon IP addresses up to date. Skipping update.")


def updateAmazonIPs():
    """Check the current S3 IP addresses are known."""
    response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json")
    with open("./config/sourceIPs.json", "wb") as output_handle:
        output_handle.write(response.json())
    # TODO: If we really want to be dealing with CSV we should just pass it
    # on from here and then return the parsed data, to be written by whatever
    # called it. Avoiding mixing I/O into random functions that aren't named
    # in an obvious way to indicate they will write it will make this harder
    # to maintain later
    parseAmazonIPs()


def parseAmazonIPs():
    """Parse the updated amazon IPs into CSV (why?)"""
    # TODO: Note that this should be CIDR notation IPv4/6 ranges
    # TODO: De-duplicate entries
    # TODO: Only use s3 ranges
    # open both IPv4 and IPv6 files in replacement mode#
    # TODO: No, don't, use a context manager around just the code writing them
    ipv4File = open("./config/sourceIPv4ranges.csv", "w")
    ipv6File = open("./config/sourceIPv6ranges.csv", "w")
    # open the sourceIPs.json file in read-only mode#
    sourceIPs = open("./config/sourceIPs.json", "r")

    for line in sourceIPs:
        if ipv4IdentString in line:
            tempLine = line.replace(ipv4IdentString, "")
            finalString = tempLine.replace(ipAddressTailString, ",")
            ipv4File.write(finalString.strip() + "\n")
        elif ipv6IdentString in line:
            tempLine = line.replace(ipv6IdentString, "")
            finalString = tempLine.replace(ipAddressTailString, ",")
            ipv6File.write(finalString.strip() + "\n")

    # TODO: If doing this without a context manager, it's best to open in a
    # try block and close with a finally
    # (but really, just use the context manager)
    ipv4File.close()
    ipv6File.close()
    sourceIPs.close()


def checkS3Root(domain):
    """Check the permissions of the root s3 bucket of a domain.
    :param domain: The domain to check.
    :return: The status code when trying to access the bucket.
    """
    testString = httpString + domain + S3BucketString
    return requests.get(testString).status_code


# function to read and parse the XML file returned when and
# list and enumerate all files within it
# parameters passed are:
#    s3BucketIn        - the response contents of the S3 root request.
#    domainIn        - the domain to be used when constructing the URLs for further requests.
def harvestRoot(s3BucketIn, domainIn):
    """Enumerate all files found in the bucket for the domain.
    :param bucket: Bucket ID to check.
    :param domain: Domain under which the bucket resides.
    """
    # TODO: FIX PARSING ERROR HERE #
    s3Tree = ET.fromstring(s3BucketIn)
    print(str(s3Tree))
    file_list = s3Tree.findall("Contents")
    print(str(file_list))
    print(str(len(file_list)) + " files found")
    for keys in file_list:
        file_name = keys.find("Key").text
        print("Attempting to download " + file_name)
        file_string = httpString + domainIn + S3BucketString + "/" + file_name
        file_contents = requests.get(file_string)
        if file_contents.status_code == 200:
            print(file_name + " opened successfully writing to ./files/" + file_name)
            file_harvester = open("%" % file_name, "wb").write(file_contents.content)
            file_harvester.close()
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
