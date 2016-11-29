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
from . import typecast, modeltypes

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
			if dataflow.element.hasName():
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
		
		"Repetition",
		"Resolution",
		"Allocation",
		"Assignment",
		"Invocation",
		"Selection",
		"Operation",
		
		"Process",
		"Context"	
		
	)
		
	def __init__( self, catalog, reporter=reporter.DefaultReporter ):
		self.report = reporter
		self.catalog = catalog
		self.contexts= []

	# FIXME: Inherit from Pass
	
	def _filterContext( self, interface ):
		return [x for x in self.contexts if isinstance(x,interface)]

	def getCurrentClosure( self ):
		res = self._filterContext(interfaces.IClosure)
		return res and res[-1] or None

	def getCurrentFunction( self ):
		res = self._filterContext(interfaces.IFunction)
		return res and res[-1] or None

	def getCurrentMethod( self ):
		res = self._filterContext(interfaces.IMethod)
		return res and res[-1] or None

	def getCurrentClass( self ):
		res = self._filterContext(interfaces.IClass)
		return res and res[-1] or None
		
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

	def typeAssignment(self, element):
		target = element.getTarget()
		value  = element.getAssignedValue()
		self._type(target)
		self._type(value)
		element.setResultAbstractType(value.getAbstractType())
		# TODO: Constrain the dataflow slot with this operaiont

	def typeAllocation(self, element):
		target = element.getSlotToAllocate()
		value  = element.getDefaultValue()
		# An allocation may not have a default value
		if value:
			element.setResultAbstractType(value.getAbstractType())
		else:
			element.setResultAbstractType(modeltypes.Any)
		# TODO: Constrain the dataflow slot with this operaiont

	def typeSelection(self, element):
		for rule in element.getRules():
			self._type(rule)

	def typeRepetition(self, element):
		self._type(element.getCondition())
		self._type(element.getProcess())

	def typeInvocation(self, element):
		self._type(element.getTarget())
		# TODO: Constraint the target type with the invocation
		# FIXME: This is false, it should be the result of the operation resolved
		# on the target
		for arg in element.getArguments():
			self._type(arg)
		element.setResultAbstractType(element.getTarget().getResultAbstractType())

	def typeResolution(self, element):
		# TODO: Rewrite this
		# FIXME: This is too basic and DIRTY !!
		assert element, "Resolution element is None"
		dataflow = self.getCurrentDataFlow()
		context   = element.getContext()
		reference = element.getReference()
		# The resolution does not have a context (it can be directly looked up)
		# in the current scope.
		if context is None:
			# A resolution without context means we have to resolve on the
			# current dataflow
			if reference.getReferenceName() == "self":
				current_class = self.getCurrentClass()
				# FIXME: Maybe we need to get the type for the instance, not
				# the type for the class
				element.setResultAbstractType(current_class.getAbstractType())
			else:
				df_slot, context_value = dataflow.resolve(reference.getReferenceName())
				if not df_slot:
					return
				slot_value = df_slot.getValue()
				# The slot may be empty (resolution fails)
				if slot_value:
					slot_value_type = slot_value.getAbstractType()
					element.setResultAbstractType(resolution_result_type)
		# The reference has a context that should be resolved first
		elif isinstance(context, interfaces.IReference):
			context_name    = context.getReferenceName()
			reference_name  = reference.getReferenceName()
			if context_name == "self":
				current_class = self.getCurrentClass()
				slot, context_value = current_class.getDataFlow().resolve(reference_name)
				# FIXME:
				# The strategy here should be: let the dataflow determine the
				# slot type. It may be the initial value, or the result of the
				# constraints.
				# so: slot_value = slot.getType()
				if slot:
					slot_value     = slot.getValue()
					element.setResultAbstractType(slot_value.getAbstractType())
			else:
				df_slot, context_value = dataflow.resolve(context.getReferenceName())
				if not df_slot:
					return
				slot_value = df_slot.getValue()
				if slot_value is None:
					if not df_slot.getAbstractType(): return
					element.setResultAbstractType(df_slot.getAbstractType())
				else:
					slot_value_type = slot_value.getAbstractType()
					assert slot_value_type
					if isinstance(slot_value_type, typecast.Context):
						resolution_result_type = slot_value_type.element(reference.getReferenceName())
						element.setResultAbstractType(resolution_result_type)
					# FIXME: I don't know what this case is for
					else:
						pass
				#df_slot, context_value = slot_value.getDataFlow().resolve(reference.getReferenceName())
				#slot_value = df_slot.getValue()
				#element.setResultAbstractType(slot_value.getAbstractType())
		elif isinstance(context, interfaces.IResolution):
			self._type(context)
		 	result_type     = context.getResultAbstractType()
			resolution_type = None
			if isinstance(result_type, typecast.Map):
				resolution_type = result_type.get(reference.getReferenceName())
				element.setResultAbstractType(resolution_type)
		# Resolving from an expression. We've got to extract the type of the
		# expression, see if the resolution can happen (does the type
		# support resolution ?), and then return the type that results from
		# the resolution.
		else:
			return
	
	def typeOperation(self, element):
		for arg in element.getOpArguments():
			self._type(arg)

def type( element ):
	catalog = modeltypes.CATALOG = Catalog()
	typer = Typer(catalog)
	catalog.make(element.getDataFlow())
	keys = list(catalog.catalog.keys())
	keys.sort()
	typer.type(element)

# EOF
