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
		added_to_parents = False
		if not isinstance(dataflow.element, interfaces.IProgram):
			# Closures don't have a name
			if hasattr(dataflow.element, "getName"):
				name = dataflow.element.getName()
				if name:
					self.parents.append(name)
					added_to_parents = True
		p = ".".join(self.parents)
		self.catalog[p] = dataflow
		for child in dataflow.children:
			self.make(child)
		if added_to_parents:
			self.parents.pop()

class Typer(object):
	
	INTERFACES = (
		
		"Resolution",
		"Allocation",
		"Assignation",
		"Invocation",
		"Operation",
		
		"Process",
		"Context"	
		
	)
		
	def __init__( self, catalog, reporter=reporter.DefaultReporter ):
		self.report = reporter
		self.catalog = catalog
		self.contexts= []

	def getCurrentDataFlow( self ):
		i = len(self.contexts) - 1
		while i >= 0:
			if self.contexts[i].hasDataFlow():
				return self.contexts[i].getDataFlow()
			i -= 1
		return None
	
	def inferType( self, element ):
		"""Infers the type for the given element."""
		return modeltypes.typeForValue(element)

	def type( self, program ):
		# FIXME: Should we ensure that the given elemen is an IProgram ?
		self.phase1(program.getDataFlow())
		self.phase2(program)

	def _type( self, element ):
		res = None
		self.contexts.append(element)
		# We iterate through the defined interfaces
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if not isinstance(element, the_interface): continue
			if not hasattr(self, "type" + name):
				raise Exception("Typer does not define type method for: %s " %(name))
			res = getattr(self, "type" + name )(element)
			break
		self.contexts.pop()
		return res

	def phase1(self, dataflow):
		# Ensures that every element of the dataflow has a basic type
		# associated to it
		for slot in dataflow.getSlots():
			slot.setType(self.inferType(slot.value))
		for child in dataflow.children:
			self.phase1(child)

	def phase2(self, element):
		self._type(element)

	def typeProcess(self, element):
		for op in element.getOperations():
			self._type(op)
	
	def typeContext(self, element):
		for slot, slot_value in element.getSlots():
			self._type(slot_value)

	def typeAssignation(self, element):
		target = element.getTarget()
		value  = element.getAssignedValue()
		element.setResultAbstractType(value.getAbstractType())
		# TODO: Constrain the dataflow slot with this operaiont

	def typeAllocation(self, element):
		target = element.getSlotToAllocate()
		value  = element.getDefaultValue()
		element.setResultAbstractType(value.getAbstractType())
		# TODO: Constrain the dataflow slot with this operaiont

	def typeInvocation(self, element):
		self._type(element.getTarget())
		# TODO: Constraint the target type with the invocation
		# FIXME: This is false, it should be the result of the operation resolved
		# on the target
		for arg in element.getArguments():
			self._type(arg)
		element.setResultAbstractType(element.getTarget().getResultAbstractType())

	def typeResolution(self, element):
		# FIXME: This is too basic and DIRTY !!
		dataflow = self.getCurrentDataFlow()
		context   = element.getContext()
		reference = element.getReference()
		if context is None:
			assert None, "Not implemented"
		elif isinstance(context, interfaces.IReference):
			df_slot, context_value = dataflow.resolve(context.getReferenceName())
			slot_value = df_slot.getValue()
			if slot_value is None:
				assert df_slot.getAbstractType()
				element.setResultAbstractType(df_slot.getAbstractType())
			else:
				slot_value_type = slot_value.getAbstractType()
				assert slot_value_type
				if isinstance(slot_value_type, typecast.Context):
					resolution_result_type = slot_value_type.element(reference.getReferenceName())
					element.setResultAbstractType(resolution_result_type)
			#df_slot, context_value = slot_value.getDataFlow().resolve(reference.getReferenceName())
			#slot_value = df_slot.getValue()
			#element.setResultAbstractType(slot_value.getAbstractType())
		else:
			return
	def typeOperation(self, element):
		for arg in element.getOpArguments():
			self._type(arg)

def type( element ):
	catalog = modeltypes.CATALOG = Catalog()
	typer = Typer(catalog)
	catalog.make(element.getDataFlow())
	keys = catalog.catalog.keys()
	keys.sort()
	typer.type(element)

# EOF
