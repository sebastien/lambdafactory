# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 22-May-2007
# -----------------------------------------------------------------------------

import interfaces, reporter

# ------------------------------------------------------------------------------
#
# DATAFLOW
#
# ------------------------------------------------------------------------------

class DataFlow:
	"""The DataFlow are ''dynamic contexts'' bound to the various program model
	elements. DataFlows are typically owned by elements which implement
	'IContext', and are linked together by rules defined in the 'Resolver'
	class.

	The dataflow bound to most expressions is the one of the enclosing closure
	(wether it is a function, or method. The dataflow of a method is bound to
	its parent class, which dataflow is also bound to the parent class dataflow.

	While 'DataFlow' and 'Context' may appear very similar, they are not the
	same: contexts are elements that keep track of declared slots, while the
	dataflow make use of the context to weave the elements togeher.
	"""

	ARGUMENT    = "Argument"
	ENVIRONMENT = "Environment"
	LOCAL       = "Local"

	def __init__( self, element, parent=None ):
		self.element  = element
		self.slots    = []
		self.parents  = []
		self.children = []
		if parent != None: self.addParent(parent)
		element.setDataFlow(self)

	def declareArgument( self, name, value ):
		self._declare(name, value, None, self.ARGUMENT)

	def declareEnvironment( self, name, value ):
		self._declare(name, value, None, self.ENVIRONMENT)

	def declareVariable( self, name, value, origin ):
		self._declare(name, value, origin, self.LOCAL)

	def _declare( self, name, value, origin, slottype ):
		"""Declares the given slot with the given name, value, origin
		and type. This is used internaly by the other 'declare' methods."""
		self.slots.append([name, value, [origin], slottype])

	def hasSlot( self, name ):
		return len(filter(lambda s:s[0]==name, self.slots)) > 0

	def getParents( self ):
		return self.parents

	def addParent( self, parent ):
		self.parents.append(parent)
		parent.addChild(self)

	def addChild( self, child ):
		assert child not in self.children
		self.children.append(child)

	def getChildren( self ):
		return self.children

	def resolve( self, name ):
		"""Returns a couple '(DataFlow slot, IElement)' or '(None,None)'
		corresponding to the resolution of the given 'name' in this dataflow."""
		slot = self.getSlot(name)
		if slot:
			return (slot, self.element)
		else:
			for p in self.getParents():
				r = p.resolve(name)
				if r: return r
			return (None,None)

	def defines( self, name ):
		slot = self.getSlot(name)
		if slot:
			return (slot, self.element)
		elif self.getChildren():
			for child in self.getChildren():
				res = child.defines(name)
				if res: return child
			return (None,None)
		else:
			return (None,None)

	def getSlot( self, name ):
		for slot in self.slots:
			if slot[0] == name: 
				return slot
		return None

# ------------------------------------------------------------------------------
#
# ABSTRACT RESOLVER
#
# ------------------------------------------------------------------------------

class AbstractResolver:
	# This defines an ordered set of interfaces names (without the leading I).
	# This list is used in the the write method
	# NOTE: When adding elements, be sure to put the *particular first*
	INTERFACES = (
		"Method",
		"Closure",
		"Class",
		"Context",
		"Process",
		"Closure",
		"Iteration",
		"Evaluation",
		"Allocation",
		"ImportOperation"
	)

	def __init__( self, reporter=reporter.DefaultReporter ):
		self.report = reporter
		self.stage2 = []

	def flow( self, program ):
		"""This is the main method of the resolver. Basically, you give a
		program, and it will either flow the whole program, or flow the given
		module (that should belong to the program).
		
		Flowing happens in two stages:
		
		 - During first stage, individual elements will have a dataflow bound to
		   them
		 - During the second stage, dataflows of all elements are linked
		   together
		
		Separating the flows allows to avoid loops (where A asks the dataflow of
		B, which cannot be created before A has a dataflow), and making the
		flowing process simpler.
		"""
		print "STAGE 1"
		self._flow(program)
		print "STAGE 2"
		while self.stage2:
			f, a = self.stage2.pop()
			f(program, *a)

	def _flow( self, element, dataflow=None ):
		"""Creates flow information for the given element."""
		res = None
		print "flowing", element
		if element.hasDataFlow():
			res = element.getDataFlow()
		else:
			# We iterate through the defined interfaces
			this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
			for name, the_interface in this_interfaces:
				if not isinstance(element, the_interface): continue
				if not hasattr(self, "flow" + name ):
					raise Exception("Resolver does not define flow method for: " + name)
				if dataflow:
					res = getattr(self, "flow" + name)(element, dataflow)
					break
				else:
					res = getattr(self, "flow" + name)(element)
					break
		return res

	def flowClass( self, element ):
		dataflow = self.flowContext(element)
		self.stage2.append((self._flowClassStage2, (element, dataflow)))	
		dataflow.declareEnvironment("self", None)
		return dataflow
	
	def _flowClassStage2( self, program, element, dataflow ):
		"""Utility function that resolves the parents for a class. This must
		happen at stage 2 because we have to wait for every class to be
		registered properly."""
		# TODO: Multiple inheritance is too complicated right now
		for p in element.getSuperClasses():
			slot, module = program.getDataFlow().resolve(p.getReferenceName())
			if not module:
				self.report.error("Undefined parent class:" + p.getReferenceName(), element)
			else:
				parent = module.getSlot(p.getReferenceName())
				flow   = parent.getDataFlow()
				dataflow.addParent(flow)

	def flowContext( self, element ):
		dataflow = DataFlow(element)
		for name, value in element.getSlots():
			dataflow.declareVariable(name, value, element)
		for name, value in element.getSlots():
			child_flow = self._flow(value)
			if child_flow:
				child_flow.addParent(dataflow)
		return dataflow

	def flowMethod( self, element ):
		dataflow  = self.flowClosure(element)
		dataflow.declareEnvironment("self", None)
		dataflow.declareEnvironment("super", None)
		return dataflow

	def flowClosure( self, element ):
		dataflow = DataFlow(element)
		for arg in element.getArguments():
			dataflow.declareArgument(arg.getReferenceName(), None)
		for op in element.getOperations():
			flow = self._flow(op, dataflow)
			if flow: flow.addParent(dataflow)
		return dataflow

	def flowProcess( self, element ):
		dataflow = DataFlow(element)
		for op in element.getOperations():
			print " +++", op
			flow = self._flow(op, dataflow)
			if flow: flow.addParent(dataflow)
		return dataflow

	def flowAllocation( self, operation, dataflow ):
		name = operation.getSlotToAllocate().getReferenceName()
		dataflow.declareVariable(name, None, operation)
		return None

	def flowIteration( self, operation, dataflow ):
		return self._flow(operation.getClosure())

	def flowEvaluation( self, operation, dataflow ):
		return self._flow(operation.getEvaluable())

	def flowImportOperation( self, operation, dataflow):
		self.stage2.append((self._flowImportOperationStage2, (operation, dataflow)))	
		print operation.getTarget().getName()
		return dataflow

	def _flowImportOperationStage2( self, program, operation, dataflow):
		program.getDataFlow().declareVariable(operation.getTarget().getName(),operation.getName(),operation)

# EOF
