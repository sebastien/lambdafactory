import interfaces

class DataFlow:

	ARGUMENT    = "Argument"
	ENVIRONMENT = "Environment"
	# FIXME: Rename to local
	VARIABLE    = "Variable"

	def __init__( self, element ):
		self.element  = element
		self.slots    = []
		self.parent   = None
		self.children = []
		element.setDataFlow(self)

	def declareArgument( self, name, value ):
		self.slots.append([name, value, [None], self.ARGUMENT])

	def declareEnvironment( self, name, value ):
		self.slots.append([name, value,[None], self.ENVIRONMENT])

	def declareVariable( self, name, value, origin ):
		self.slots.append([name, value, [origin], self.VARIABLE])

	def getParent( self ):
		return self.parent

	def setParent( self, parent ):
		self.parent = parent
		parent.addChild(self)
	
	def addChild( self, child ):
		assert child not in self.children
		self.children.append(child)
	
	def getChildren( self ):
		return self.children

	def resolve( self, name ):
		slot = self.getSlot(name)
		if slot:
			return self.element
		elif self.getParent():
			return self.getParent().resolve(name)
		else:
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

	def __init__( self ):
		pass

	def flow( self, element, dataflow=None ):
		"""Creates flow information for the given element."""
		if element.hasDataFlow():
			return element.getDataFlow()
		# We iterate through the defined interfaces
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if not isinstance(element, the_interface): continue
			if not hasattr(self, "flow" + name ):
				raise Exception("Resolver does not define flow method for: " + name)
			if dataflow:
				return getattr(self, "flow" + name)(element, dataflow)
			else:
				return getattr(self, "flow" + name)(element)
		return None

	def flowClass( self, element ):
		dataflow = self.flowContext(element)
		dataflow.declareEnvironment("self", None)
		return dataflow

	def flowContext( self, element ):
		dataflow = DataFlow(element)
		for name, value in element.getSlots():
			dataflow.declareVariable(name, value, element)
		for name, value in element.getSlots():
			child_flow = self.flow(value)
			if child_flow:
				child_flow.setParent(dataflow)
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
			flow = self.flow(op, dataflow)
			if flow: flow.setParent(dataflow)
		return dataflow

	def flowProcess( self, element ):
		dataflow = DataFlow(element)
		for op in element.getOperations():
			flow = self.flow(op, dataflow)
			if flow: flow.setParent(dataflow)
		return dataflow

	def flowAllocation( self, operation, dataflow ):
		name = operation.getSlotToAllocate().getReferenceName()
		dataflow.declareVariable(name, None, operation)
		return None

	def flowIteration( self, operation, dataflow ):
		dataflow.declareVariable(
			operation.getIteratedSlot().getReferenceName(), 
			# FIXME: Should give iterator...
			None,
			operation
		)
		return self.flow(operation.getProcess())

	def flowEvaluation( self, operation, dataflow ):
		return self.flow(operation.getEvaluable())


# EOF
