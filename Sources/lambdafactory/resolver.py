# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 06-Dec-2006
# -----------------------------------------------------------------------------

import interfaces, reporter

class DataFlow:

	ARGUMENT    = "Argument"
	ENVIRONMENT = "Environment"
	# FIXME: Rename to local
	VARIABLE    = "Variable"

	def __init__( self, element ):
		self.element  = element
		self.slots    = []
		self.parents  = []
		self.children = []
		element.setDataFlow(self)

	def declareArgument( self, name, value ):
		self.slots.append([name, value, [None], self.ARGUMENT])

	def declareEnvironment( self, name, value ):
		self.slots.append([name, value,[None], self.ENVIRONMENT])

	def declareVariable( self, name, value, origin ):
		self.slots.append([name, value, [origin], self.VARIABLE])
		#print "declare", name, value, self.hasSlot(name)
		#self.element.setSlot(name, value, False)

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
		# FIXME: For the moment, resolve returns the scope in which the
		# given slot is defined... this is very confusing
		slot = self.getSlot(name)
		if slot:
			return self.element
		else:
			for p in self.getParents():
				r = p.resolve(name)
				if r: return r
			return None

	def defines( self, name ):
		slot = self.getSlot(name)
		if slot:
			return self.element
		elif self.getChildren():
			for child in self.getChildren():
				res = child.defines(name)
				if res: return child
			return None
		else:
			return None

	def getSlot( self, name ):
		for slot in self.slots:
			if slot[0] == name: 
				return slot
		return None
		
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
		"Allocation",
		"Iteration",
		"Evaluation"
	)

	def __init__( self, reporter=reporter.DefaultReporter ):
		self.report = reporter
		self.stage2 = []
		
	def flow( self, module, program=None):
		if program == None: program = module
		self._flow(module)
		while self.stage2:
			f, a = self.stage2.pop()
			f(program, *a)
	
	def _flow( self, element, dataflow=None ):
		"""Creates flow information for the given element."""
		res = None
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
				else:
					res = getattr(self, "flow" + name)(element)
		return res

	def flowClass( self, element ):
		dataflow = self.flowContext(element)
		self.stage2.append((self._flowClassStage2, (element, dataflow)))	
		dataflow.declareEnvironment("self", None)
		return dataflow
	
	def _flowClassStage2( self, program, element, dataflow ):
		# TODO: Multiple inheritance is too complicated right now
		for p in element.getSuperClasses():
			module = program.getDataFlow().resolve(p.getReferenceName())
			if not module:
				self.report.error("Undefined parent class:" + p.getReferenceName(), element)
				self.report = reporter
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

# EOF
