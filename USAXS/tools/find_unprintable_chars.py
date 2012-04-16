#!/usr/bin/env python

import sys
import os.path

printableCharsList = [9, 10, 13] + range(32,127)
printableCharsStr = "".join([chr(x) for x in printableCharsList])

def findUnprintables(file):
	someBad = False
	fmt = "file=%s, line=%i, column=%i, char=%i (decimal)"
	i = 0
	for line in open(file, "r"):
		i += 1
		j = 0
		for character in line:
			j += 1
			if character not in printableCharsStr:
				print fmt % (file, i, j, ord(character))
				someBad = True
	return someBad

if __name__ == "__main__":
	if len(sys.argv) == 2:
		if os.path.exists(sys.argv[1]):
			if os.path.isfile(sys.argv[1]):
				status = findUnprintables(sys.argv[1])
				sys.exit(status)
			else:
				print "%s is not a regular file" % sys.argv[1]
				sys.exit(4)
		else:
			print "%s does not exist" % sys.argv[1]
			sys.exit(3)
	else:
		print "Usage: find_unprintable_chars.py filename"
		sys.exit(2)
