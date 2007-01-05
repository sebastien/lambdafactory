# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 06-Dec-2006
# Last mod  : 06-Dec-2006
# -----------------------------------------------------------------------------

import sys

class Reporter:
	"""The reporter aggregates error reports that may happen during model
	construction and the different phases (dataflowing, typing, writing,
	etc)."""

	def __init__( self ):
		self.warnings   = []
		self.errors     = []
		self._onWarning = []
		self._onError   = []

	def warning( self, message, element=None ):
		self.warning.append(message)
		map( lambda c:c(message, element), self._onWarning)

	def error( self, message, element=None ):
		self.errors.append(message)
		map( lambda c:c(message, element), self._onError)

	def onError( self, callback ):
		self._onError.append(callback)

	def onWarning( self, callback ):
		self._onWarning.append(callback)

	def echoError( self, message, element ):
		sys.stderr.write("[!] %s\n    at %s\n" % (message, element))

	def echoWarning( self, message, element ):
		sys.stderr.write("[-] %s\n    at %s\n" % (message, element))

DefaultReporter = Reporter()
DefaultReporter.onError(DefaultReporter.echoError)
DefaultReporter.onWarning(DefaultReporter.echoWarning)

# EOF