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
		self._alreadyDone = {}
		self._indent    = 0

	def indent( self ):
		self._indent += 1

	def dedent( self ):
		self._indent -= 1

	def isDone(self, message, element, update=True):
		key = "%s:%s" % (message, element)
		if key in self._alreadyDone:
			return True
		if update:
			self._alreadyDone[key] = 1
		return False

	def warning( self, message, element=None ):
		if self.isDone(message, element): return
		self.warnings.append(message)
		list(map( lambda c:c(message, element), self._onWarning))

	def error( self, *message ):
		self.errors.append(message)
		list(map( lambda c:c(message), self._onError))

	def trace( self, *message):
		pass

	def info( self, *message):
		sys.stderr.write(" -  %s%s\n" % ((" " * self._indent) , " ".join(map(str, message))))

	def onError( self, callback ):
		self._onError.append(callback)

	def onWarning( self, callback ):
		self._onWarning.append(callback)

	def echoError( self, message ):
		sys.stderr.write("[!] %s\n" % (" ".join(map(str,message))))

	def echoWarning( self, message, element ):
		sys.stderr.write("[-] %s at %s\n" % (message, element))

DefaultReporter = Reporter()
DefaultReporter.onError(DefaultReporter.echoError)
DefaultReporter.onWarning(DefaultReporter.echoWarning)

# EOF
