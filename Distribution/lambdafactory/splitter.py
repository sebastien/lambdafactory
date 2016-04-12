#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import os
__module_name__ = 'lambdafactory.splitter'
SNIP_START = '8< ---['
SNIP_END = ']---'
SNIP = ((SNIP_START + '%s') + SNIP_END)
class FileSplitter:
	"""Some languages (like Java or ActionScript) may generate multiple files
	for one single module. The FileSplitter makes it easy for front-end to
	produce multiple file from a single file or text generated by the
	LambdaFactory back-end writers."""
	"""Initializes the file splitter with the given output directory"""
	def __init__ (self, outputPath):
		self.outputDir = None
		self.currentFilePath = None
		self.currentFile = None
		self.outputDir = outputPath

	def start(self):
		"""Callback invoked when a 'fromXXX' method is invoked."""
		self.currentFilePath = None
		self.currentFile = None
		return self.currentFile

	def end(self):
		"""Callback invoked after a 'fromXXX' method was invoked"""
		self.currentFile.close()
		self.currentFilePath = None
		self.currentFile = None
		return self.currentFile

	def newFile(self, path):
		path = os.path.join(self.outputDir, path)
		parents=os.path.dirname(path)
		if (not os.path.exists(parents)):
			os.makedirs(parents)
		self.currentFile = file(path, 'w')
		return self.currentFile

	def writeLine(self, line):
		"""Writes the given line to the current file"""
		if (self.currentFile is None):
			raise ERR_MUST_START_WITH_SNIP
		elif True:
			return self.currentFile.write(line)

	def fromStream(self, stream, addEOL=None):
		if addEOL is None: addEOL = False
		self.start()
		for line in stream:
			i=line.find(SNIP_START)
			j=line.rfind(SNIP_END)
			if (((i >= 0) and (j > i)) and (((j >= len(line)) - 1) - len(SNIP_END))):
				path=line[(i + len(SNIP_START)):j]
				self.newFile(path)
			elif True:
				self.writeLine((line + ((addEOL and '\n') or '')))
		return self.end()

	def fromLines(self, lines, addEOL=None):
		if addEOL is None: addEOL = False
		return self.fromStream(lines, addEOL)

	def fromString(self, text):
		return self.fromLines(text.split('\n'), addEOL=(True))


