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
		"Context",
		"Process",
		"Allocation",
		"Iteration",
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

	def flowContext( self, element ):
		dataflow = DataFlow(element)
		for name, value in element.getSlots():
			dataflow.declareVariable(name, value, element)
			child_flow = self.flow(value)
			if child_flow: child_flow.setParent(dataflow)
		return dataflow

	# TODO: Flow class defines this

	def flowMethod( self, element ):
		dataflow  = self.flowClosure(element)
		dataflow.declareEnvironment("self", None)
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
		dataflow.declareVariable(name, None, element)
		return None

	def flowIteration( self, operation, dataflow ):
		dataflow.declareVariable(
			operation.getIteratedSlot().getReferenceName(), 
			# FIXME: Should give iterator...
			None,
			operation
		)
		return self.flow(operation.getProcess())

class Pouet:

	def evaluate( self, element ):
		res = None
		if element is None: return ""
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if isinstance(element, the_interface):
				if not hasattr(self, "evaluate" + name ):
					raise Exception("Resolve does not define evaluate method for: "
					+ name)
				else:
					return getattr(self, "evaluate" + name)(element)
		return self.nop
		#print ("[!] Element not supported by resolver: " + str(element))

	def nop( self ):
		pass

	def evaluateContext( self, element ):
		self.pushContext(element)
		for name, value in element.getSlots():
			self.declareSlot(name, element)
		return self.popContext

	def evaluateMethod( self, element ):
		self.pushContext(element)
		for arg in element.getArguments():
			self.declareSlot(arg.getReferenceName(), element)
		self.declareSlot("self", element)
		return self.popContext

	def evaluateClosure( self, element ):
		self.pushContext(element)
		for arg in element.getArguments():
			self.declareSlot(arg.getReferenceName(), element)
		return self.popContext

	def evaluateBlock( self, element ):
		self.pushContext(element)
		return self.popContext

	def evaluateProcess( self, element ):
		if not isinstance(element, interfaces.IProcess):
			return self.nop
		return self.nop

	def evaluateAllocation( self, operation ):
		name = operation.getSlotToAllocate().getReferenceName()
		self.declareSlot(name, self.getContext())
		return self.nop

	def evaluateIteration( self, operation ):
		self.pushContext(operation)
		self.declareSlot(operation.getIteratedSlot().getReferenceName(), operation)
		return self.popContext

# EOF