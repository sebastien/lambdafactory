# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 14-Aug-2007
# Last mod  : 14-Aug-2007
# -----------------------------------------------------------------------------

import interfaces, reporter
import typecast, modeltypes

# ------------------------------------------------------------------------------
#
# Typer Class
#
# ------------------------------------------------------------------------------

class Catalog(object):

	def __init__(self):
		self.catalog = {}
		self.parents = []

	def get(self, symbol):
		flow = self.catalog[symbol]
		return flow.element

	def make(self, dataflow):
		if not isinstance(dataflow.element, interfaces.IProgram):
			self.parents.append(dataflow.element.getName())
		p = ".".join(self.parents)
		self.catalog[p] = dataflow
		for child in dataflow.children:
			self.make(child)
		if not isinstance(dataflow.element, interfaces.IProgram):
			self.parents.pop()

class Typer(object):
	
	def __init__(self, catalog):
		self.catalog = catalog

	def inferType( self, element ):
		"""Infers the type for the given element."""
		if isinstance(element, interfaces.IList):
			list_interface = self.catalog.get("DataTypes.List")
			return list_interface
		else:
			return None

	def walk(self, dataflow):
		for slot in dataflow.getSlots():
			slot.setType(self.inferType(slot.value))
		for child in dataflow.children:
			self.walk(child)

def type( element ):
	catalog = Catalog()
	typer = Typer(catalog)
	catalog.make(element.getDataFlow())
	keys = catalog.catalog.keys()
	keys.sort()
	#if True:
	#	for key in keys:
	#		print key
	typer.walk(element.getDataFlow())

# EOF
