# encoding: utf8
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2017-01-16
# Last mod  : 2017-11-16
# -----------------------------------------------------------------------------

import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter
from   lambdafactory.languages.javascript.writer import Writer as JavaScriptWriter

#------------------------------------------------------------------------------
#
#  WRITER
#
#------------------------------------------------------------------------------

class Writer(JavaScriptWriter):

	def onSingleton( self, element ):
		return "/* singleton */"

	def onTrait( self, element ):
		return "/* trait */"

	def onClass( self, element ):
		"""Writes a class element."""
		parents = self.getClassParents(element)
		return "/* class */"

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
