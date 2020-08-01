#!/usr/bin/env python3
# pailfrog.py - Amazon S3 bucket investigation tool, written in Python3 #

# imports block begins #
import sys, getopt, requests					# system, parameters and requests functionality.
import socket									# socket connection required to get IP address of domain.
import csv										# csv read/write functionality required for reading Amazon IP addresses.
from ipaddress import ip_address, ip_network 	# IP address and address range functionality.
# imports block ends #

# global variable definition block begins #
s3List = []		# an empty list to contain all the S3 IPV4 ranges.
resultList = []	# an empty list to contain all the IP addresses which are in the S3 IPV4 range.

ipv4IdentString = "\"ip_prefix\": \""
ipv6IdentString = "\"ipv6_prefix\": \""
ipAddressTailString = "\","
# global variable definition block begins #

# main function begins #
def main(argv):
	testDomain = str(sys.argv)
	print("Retrieving updated Amazon IP ranges...")
	updateAmazonIPs()							# start by updating Amazon IP addresses.
	print("Ranges updated successfully.")
	currentIPAddress = socket.gethostbyname(testDomain)
	#for item in list
		#read next item,
	if checkInRange(currentIPAddress, currentRange):
		resultList.append(item)
	for x in resultList:
		print ("Domain: " + resultList[x] + " is hosted in Amazon S3 at" + currentIPAddress)
	sys.exit(0)
# main function ends #

# short function to ensure that the current S3 IP addresses are known to the program #
def updateAmazonIPs():
	sourceIPs = open("./config/sourceIPs.json", "w")
	sourceIPs = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json')
	sourceIPs.close()
	parseAmazonIPs()
# end updateAmazonIPs #

# a function to parse the results of updateAmazonIPs() into a usable .csv	#
# file of CIDR notation IPV4 ranges and another of IPV6 ranges				#
def parseAmazonIPs():
	# open both IPv4 and IPv6 files in replacement mode#
	ipv4File = open("./config/sourceIPv4ranges.csv", "w")
	ipv6File = open("./config/sourceIPv6ranges.csv", "w")
	# open the sourceIPs.json file in read-only mode#
	sourceIps = open("./config/sourceIPs.json", "r")
	# iterate through file, parse out IP addresses to files #
	for line in sourceIps:
			if ipv4IdentString in line:
				tempLine = line.replace(ipv4IdentString, "")
				finalString = tempLine.replace(ipAddressTailString, ",")
				ipv4File.write(finalString)
			elif ipv6IdentString in line:
				tempLine = line.replace(ipv6IdentString, "")
				finalString = tempLine.replace(ipAddressTailString, ",")
	# close up all the files #
	ipv4File.close()
	ipv6File.close()
	sourceIPs.close()
# end parseAmazonIPs #	

# short function that checks if an IP address is in a CIDR range.
# parameters passed are:
#	ipAddressIn 	-	address to check
#	rangeIn			-	range to check in
def checkInRange(ipAddressIn, rangeIn):
	if 	ip_address(ipAddressIn) in rangeIn:
		result = true
	else:
		result = false
	return result
# end checkInRange()#