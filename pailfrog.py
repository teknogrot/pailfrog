#!/usr/bin/env python3
# pailfrog.py - Amazon S3 bucket investigation tool, written in Python3 #

# imports block begins #
import os							# operating system functionality.
import sys, getopt, requests					# system, parameters and requests functionality.
import socket							# socket connection required to get IP address of domain.
import csv							# csv read/write functionality required for reading Amazon IP addresses.
import json							# json handling for the Amazon data.
import xml.etree.ElementTree as ET				# xml handling for the S3 directory listing.
import ipaddress						# IP address and address range functionality.
import time						 	# time functionality.
import datetime							# date functioanlity.
# imports block ends #

# global variable definition block begins #
s3List = []							# an empty list to contain all the S3 IPV4 ranges.
resultList = []							# an empty list to contain all the IP addresses which are in the S3 IPV4 range.
fileList = []							# an empty list to contain all files identified in the root of an S3 bucket.
# global variable definition block ends #


# string variable definition block ends #
ipv4IdentString = "\"ip_prefix\": \""
ipv6IdentString = "\"ipv6_prefix\": \""
ipAddressTailString = "\","
httpString = "http://"
S3BucketString = ".s3.amazonaws.com"
keyLineStartString = "<Key>"
keyLineEndString = "</Key>"
# string variable definition block ends #

# main function begins #
def main(argv):
	testDomain = str(sys.argv[1])
	doAmazonTest = "junkdata"
	startTime = datetime.datetime.now()
	runTimeString = startTime.strftime("%Y%m%d%H%M%S")
	print("Task started at: " + startTime.strftime("%H:%M:%S, %d/%m/%Y"))
	projectFolder = createFolder(testDomain, runTimeString)
	print("Creating folder: " + projectFolder)

	## numberOfDays = rangeDateCheck()
	# print("Amazon IP ranges last updated " + numberOfDays + " ago.")
	while doAmazonTest not in ('y', 'Y', 'n', 'N'):
		doAmazonTest = input("Update Amazon IP ranges? Y/N ")
		if doAmazonTest == 'y' or doAmazonTest == 'Y':
			print("Retrieving updated Amazon IP ranges...")
			updateAmazonIPs()						# start by updating Amazon IP addresses.
			print("Ranges updated successfully.")
		elif doAmazonTest == 'n' or doAmazonTest == 'N':
			print("Skipping Amazon range update")

	print("Testing hostname: '" + testDomain + "'.")
	currentIPAddress = socket.gethostbyname(testDomain)
	print("IP address of host is: " + currentIPAddress)

	# open sourceIPv4ranges.csv in read-only mode.
	with open("./config/sourceIPv4ranges.csv", "r") as sourceIPs:
		for line in sourceIPs:
			tempLine = line.replace(",\n", "")					# prune out the comma and newline from the line of the .csv,
			currentRange = ipaddress.ip_network(tempLine)				# convert to IP address
			if checkInRange(currentIPAddress, currentRange):
				resultList.append("Domain: \"" + testDomain + "\" is hosted in Amazon S3 at: " + currentIPAddress + "\n")

	# print out the domains which successfully resolved and check if the root is accessible.
	for item in resultList:
		print (item)
		s3Root = checkS3Root(testDomain)
		httpCode = s3Root.status_code
		if httpCode == 200:
			print("HTTP response for " + httpString + testDomain + S3BucketString + " is: " + str(httpCode))
			print("S3 root directory is publicly listable. Enumerating files.")
			harvestRoot(s3Root.content, testDomain, projectFolder)
		else:
			print("HTTP response for " + httpString + testDomain + S3BucketString + " is: " + str(httpCode))
	sys.exit(0)
# main function ends #

# a short function to check how many days it has been since the Amazon ranges have been updated
#def rangeDateCheck():
#	if os.path.isfile("./config/sourceIPs.json"):
#		fileModifiedOn = os.path.getmtime(./config/sourceIPs.json)
#		print("File updated on: " + str(fileModifiedOn))
#		currentTime = datetime.now()
#		print("Current time: " + str(currentTime))
#		tempTime = currentTime - fileModifiedOn
#		print("Diff is: " + str(tempTime))
#		if (currentTime - fileModifiedOn) > 86400:
#			updateAmazonIPs()
#		else:
#			print("Amazon IP addresses up to date. Skipping update.")
# end rangeDateCheck #

# a short function to create a new folder for the input domain #
def createFolder(folderNameIn, timeStringIn):
	directoryPath = "./output/" + folderNameIn + "_" + timeStringIn
	permissions = 0o744
	try:
		os.makedirs(directoryPath, permissions)
	except OSError:
		print ("Directory creation for %s failed" % directoryPath)
		return directoryPath
	else:
		print ("Directory creation for %s succeeded" % directoryPath)
		return directoryPath
# createFolder ends #


# short function to ensure that the current S3 IP addresses are known to the program #
def updateAmazonIPs():
	response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json")
	#responseJsonified = response.json()
	#sourceIPs.write(responseJsonified)
	with open("./config/sourceIPs.json", "wb") as sourceIPs:
		sourceIPs.write(response.content)
	parseAmazonIPs()
# end updateAmazonIPs #

# a function to parse the results of updateAmazonIPs() into a usable .csv	#
# file of CIDR notation IPV4 ranges and another of IPV6 ranges				#
# needs logic to de-duplicate entries and properly process .json elements	#
# to only use S3 ranges														#
def parseAmazonIPs():
	# open both IPv4 and IPv6 files in replacement mode#
	ipv4File = open("./config/sourceIPv4ranges.csv", "w")
	ipv6File = open("./config/sourceIPv6ranges.csv", "w")
	# open the sourceIPs.json file in read-only mode#
	#sourceIPs = open("./config/sourceIPs.json", "r")
	with open("./config/sourceIPs.json", "r") as sourceIPs:
		#sourceIPsDictionary = json.load(sourceIPs)
		# handle IPv4
		#for prefixes in sourceIPsDictionary:
		#	print(sourceIPsDictionary[prefixes])
		#	if prefixes['service'] == 'S3':
		#		ipv4File.write(prefix['ip_prefix'] + ",\n")
		# handle PIv6
		#for ipv6_prefixes in sourceIPsDictionary:
		#	if ipv6_prefixes['service'] == "S3":
		#		ipv6File.write(prefix['ipv6_prefix'] + ",\n")

		# iterate through file, parse out IP addresses to files #
		for line in sourceIPs:
			if ipv4IdentString in line:
				tempLine = line.replace(ipv4IdentString, "")
				finalString = tempLine.replace(ipAddressTailString, ",")
				ipv4File.write(finalString.strip() + "\n")
			elif ipv6IdentString in line:
				tempLine = line.replace(ipv6IdentString, "")
				finalString = tempLine.replace(ipAddressTailString, ",")
				ipv6File.write(finalString.strip() + "\n")
	# close up all the files #
	ipv4File.close()
	ipv6File.close()
# end parseAmazonIPs #

# short function that checks if an IP address is in a CIDR range.
# parameters passed are:
#	ipAddressIn 	-	address to check
#	rangeIn			-	range to check in
def checkInRange(ipAddressIn, rangeIn):
	if 	ipaddress.ip_address(ipAddressIn) in rangeIn:
		result = True
	else:
		result = False
	return result
# end checkInRange() #

# short function to check the permissions on the root directory 
# of the S3 bucket and return the HTTP code
# parameter passed is:
# 	domainIn		- the same domain as passed by the args.
def checkS3Root(domainIn):
	testString = httpString + domainIn + S3BucketString
	rootResponse = requests.get(testString)
	return rootResponse
# end checkS3Root #

# short function to find XML tags from S3 bucket root XML file#
def findXMLTags(tree, tag):
    results = []
    for node in tree:
        if node.tag.split('}')[-1] == tag:
            results.append(node)
    return results
# end findXMLTags

# function to read and parse the XML file returned when and
# list and enumerate all files within it
# parameters passed are:
#       s3BucketIn              - the response contents of the S3 root request.
#       domainIn                - the domain to be used when constructing the URLs for further requests.
def harvestRoot(s3BucketIn, domainIn, directoryPathIn):
	s3Tree = ET.fromstring(s3BucketIn)
	fileList = findXMLTags(s3Tree, "Contents")
	results = {}
	print(str(len(fileList)) + " files found. Attempting download")
	# for every file found, try open that file and download it if successful #
	for keys in fileList:
		fileName = findXMLTags(keys, "Key")[0].text
		print("Attempting to download " + fileName)
		fileString = httpString + domainIn + S3BucketString + "/" + fileName
		fileContents = requests.get(fileString)
		if fileContents.status_code == 200:
			filePath = directoryPathIn + "/" + fileName
			print("File " + fileName + " opened successfully (status code 200). Writing to: " + filePath)
			with open("./%s" %filePath, "wb") as fileHarvester:
				fileHarvester.write(fileContents.content)
			fileHarvester.close()
		elif fileContents.status_code == 403:
			print(fileName + "status code 403: permission denied.")
		elif fileContents.status_code == 404:
			print(fileName + "status code 404: file not found.")
		else:
			print(fileName + "file download failed with status code: " + str(fileContents.status_code))
# end harvestRoot() #

# run main #
if __name__ == "__main__":
    main(sys.argv[1:])

