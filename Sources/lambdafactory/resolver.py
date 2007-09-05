# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 05-Sep-2007
# -----------------------------------------------------------------------------

import interfaces, reporter

# STAGE2: Linking classes/modules/symbols together
# STAGE3: Linking operations to their original dataflowslot

# ------------------------------------------------------------------------------
#
# DATAFLOW
#
# ------------------------------------------------------------------------------

class DataFlowSlot:

	def __init__(self, name, value, origin, type):
		assert name
		self.name = name
		self.value = value
		self.origin = origin
		self.slotType = type
		self.operations = []
		self.type = None

	def getValue(self):
		return self.value

	def getAbstractType(self):
		return self.type

	def addOperation(self,operation):
		"""Adds an operation made to this dataflow slot."""
		self.operations.append(operation)

	def setType(self, typeInfo):
		"""Sets the type information attached to this slot. The type information
		should be a typecast type instance."""
		return self.type

	def getDeclaredType(self):
		pass

	def getInitialValue(self):
		pass

	def getType(self):
		"""Returns the typecast type description for the value associated to
		that slot."""
		# FIXME: Do resolution of operation to get the final type
		return self.type

	def __str__(self):
		return '<Slot("%s"=%s):%s@%s%s>' % (self.name, self.value, self.type, self.slotType, self.origin)

class DataFlow(interfaces.IDataFlow):
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
	IMPORTED    = "Imported"

	def __init__( self, element, parent=None ):
		self.element  = element
		self.slots    = []
		self.parents  = []
		self.children = []
		if parent != None: self.addParent(parent)
		element.setDataFlow(self)

	# FIXME: ARgument should be 'element' rather than 'value'
	def declareArgument( self, name, value ):
		self._declare(name, value, None, self.ARGUMENT)

	def declareEnvironment( self, name, value ):
		self._declare(name, value, None, self.ENVIRONMENT)

	def declareVariable( self, name, value, origin ):
		self._declare(name, value, origin, self.LOCAL)

	def declareImported( self, name, value, origin ):
		self._declare(name, value, origin, self.IMPORTED)
		
	def _declare( self, name, value, origin, slottype ):
		"""Declares the given slot with the given name, value, origin
		and type. This is used internaly by the other 'declare' methods."""
		self.slots.append(DataFlowSlot(name, value, [origin], slottype))

	def getSlots( self ):
		"""Returns the slots defiend for this dataflow."""
		return self.slots
	
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
			#print "FOUND !"
			return (slot, self.element)
		else:
			for p in self.getParents():
				r = p.resolve(name)
				if r != (None,None):
					return r
			return (None,None)

	def defines( self, name ):
		slot = self.getSlot(name)
		if slot:
			return (slot, self.element)
		elif self.getChildren():
			for child in self.getChildren():
				res = child.defines(name)
				# FIXME: I think it should be child.getSlot(name), child
				if res: return child
			return (None,None)
		else:
			return (None,None)

	def getSlot( self, name ):
		for slot in self.slots:
			if slot.name== name: 
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
		
		"Iteration",
		"Repetition",
		"Evaluation",
		"Allocation",
		"Assignation",
		"ImportOperation",
	
		"Program",
		"Process",
		"Context"	
		
	)

	def __init__( self, reporter=reporter.DefaultReporter ):
		self.report = reporter
		self.stage2 = []
		self.stage3 = []
		self.context = []

	def captureContext(self):
		"""Returns a copy of the current flowing context. This is helpful
		for 'stage 2' flowing operations."""
		res = []
		for c in self.context: res.append(c)
		return res

	def _findParentModule( self, element ):
		"""Finds the parent module for the given context element."""
		assert isinstance(element, interfaces.IContext)
		while element.getParent() and not isinstance(element.getParent(), interfaces.IModule):
			parent = element.getParent()
		return element.getParent()

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
		self._flow(program)
		while self.stage2:
			f, a = self.stage2.pop()
			f(program, *a)
		while self.stage3:
			f, a = self.stage3.pop()
			f(program, *a)

	def getCurrentDataFlow( self ):
		i = len(self.context) - 1
		while i >= 0:
			if self.context[i].hasDataFlow():
				return self.context[i].getDataFlow()
			i -= 1
		return None
	
	def _flow( self, element, dataflow=None ):
		"""Creates flow information for the given element."""
		res = None
		self.context.append(element)
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
			if not element.hasDataFlow():
				element.setDataFlow(self.getCurrentDataFlow())
		self.context.pop()
		return res

	def flowClass( self, element ):
		dataflow = self.flowContext(element)
		self.stage3.append((self._flowClassStage3, (self.captureContext(), element, dataflow)))
		dataflow.declareEnvironment("self", None)
		return dataflow

	def _flowClassStage3( self, program, context, element, dataflow ):
		"""Utility function that resolves the parents for a class. This must
		happen at stage 2 because we have to wait for every class to be
		registered properly."""
		# TODO: Multiple inheritance is too complicated right now
		for p in element.getParentClasses():
			slot         = None
			this_module  = tuple(e for e in context if isinstance(e,interfaces.IModule))
			this_program = tuple(e for e in context if isinstance(e,interfaces.IProgram))
			imported_class = p.getReferenceName()
			if this_module:
				this_module = this_module[0]
				slot, defined_in = this_module.getDataFlow().resolve(p.getReferenceName())
			if slot is None and this_program:
				this_program = this_program[0]
				slot, defined_in = this_program.getDataFlow().resolve(p.getReferenceName())
			if not defined_in or not slot or not slot.getValue():
				self.report.error("Undefined parent class:" + p.getReferenceName(), element)
			else:
				parent_class = slot.getValue()
				class_flow   = parent_class.getDataFlow()
				dataflow.addParent(class_flow)
				# We assert that the inheritance works
				for parent_slot in class_flow.getSlots():
					assert dataflow.resolve(slot.name)

	def flowContext( self, element, dataflow=None ):
		if dataflow is None: dataflow = DataFlow(element)
		for name, value in element.getSlots():
			dataflow.declareVariable(name, value, element)
		for name, value in element.getSlots():
			child_flow = self._flow(value)
			if child_flow:
				child_flow.addParent(dataflow)
		return dataflow

	def flowProgram( self, element ):
		dataflow = DataFlow(element)
		# TODO: Call the runtime for setting variables
		# TODO: Add symbolic values for this
		dataflow.declareEnvironment("Undefined", None)
		dataflow.declareEnvironment("True", None)
		dataflow.declareEnvironment("False", None)
		dataflow.declareEnvironment("Null", None)
		for module in element.getModules():
			module_flow = self._flow(module)
			# FIXME: This never happens, and I don't get why
			if module_flow in dataflow.children:
				module_flow.addParent(dataflow)
				raise None
			else:
				pass
		return self.flowContext(element, dataflow)

	def flowMethod( self, element ):
		dataflow  = self.flowClosure(element)
		dataflow.declareEnvironment("self", None)
		dataflow.declareEnvironment("super", None)
		return dataflow

	def flowClosure( self, element ):
		dataflow = DataFlow(element)
		dataflow.declareEnvironment("target", None)
		for arg in element.getArguments():
			dataflow.declareArgument(arg.getName(), arg)
		for op in element.getOperations():
			flow = self._flow(op, dataflow)
			if flow: flow.addParent(dataflow)
		return dataflow

	def flowProcess( self, element, dataflow=None ):
		if dataflow is None: dataflow = DataFlow(element)
		#dataflow = DataFlow(element)
		if isinstance(element, interfaces.IContext):
			self.flowContext(element, dataflow)
		for op in element.getOperations():
			flow = self._flow(op, dataflow)
			if flow: flow.addParent(dataflow)
		return dataflow

	def flowAllocation( self, operation, dataflow ):
		name = operation.getSlotToAllocate().getName()
		dataflow.declareVariable(name, operation.getDefaultValue(), operation)
		return None

	def flowAssignation(self, operation, dataflow):
		# TODO
		self.stage3.append((self._flowAssignationStage3, (self.captureContext(), operation, dataflow)))

	def getContextDataflow(self, context):
		i = len(context) - 1
		while i > 0:
			if context[i].hasDataFlow(): return context[i].getDataFlow()
			i -= 1
		assert None, "No dataflow associated to context elements"
	
	def resolve( self, value, context ):
		if type(value) in (str, unicode):
			dataflow = self.getContextDataflow(context)
			return dataflow.resolve(value)
		elif isinstance(value, interfaces.IReference):
			return self.resolveReference(value, context)
		elif isinstance(value, interfaces.IResolution):
			return self.resolveResolution(value, context)
		else:
			self.report.warning("resolver.resolve: Cannot resolve: %s" % (value))
			return None, None
			#raise Exception("Cannot resolve: %s" % (value))

	def resolveReference( self, reference, context ):
		assert isinstance(reference, interfaces.IReference), reference
		name = reference.getReferenceName()
		dataflow = self.getContextDataflow(context)
		return dataflow.resolve(name)
	
	def resolveResolution(self, resolution, context):
		assert isinstance(resolution, interfaces.IResolution)
		resolution_context  = resolution.getContext()
		resolution_reference = resolution.getReference()
		if resolution_context:
			slot, context_value = self.resolve(resolution_context, context)
			if slot is None:
				return None, None
			c = [] ; c.extend(context) ; c.append(context_value)
			return self.resolveReference(resolution_reference, c)
		else:
			return self.resolveReference(resolution_reference, context)
			
	def _flowAssignationStage3( self, program, context, operation, dataflow ):
		target = operation.getTarget()
		slot, context = self.resolve(target, context)
		# FIXME: This means there was a problem in the resolution scheme...
		if slot:
			slot.addOperation(operation)

	def flowIteration( self, operation, dataflow ):
		# We get the closure arguments which will be assigned during each
		# iteration.
		closure = operation.getClosure()
		args  = map(lambda a:a.getName(), closure.getArguments())
		# Here we cheat a little bit, as the iteration is an operation, not
		# a context, we use the process attached to the iteration as a context
		# and define the slots in its dataflow that correspond to the first two
		# arguments (iterated value, iteartion count)
		child_flow  = self._flow(operation.getClosure())
		for i in range(0,min(len(args),2)):
			child_flow.declareVariable(args[i], None, operation)
		# FIXME: This does not work...
		# flow = DataFlow(operation)
		# child_flow.addParent(flow)
		return child_flow

	def flowRepetition(self, operation, dataflow):
		return self._flow(operation.getProcess())

	def flowEvaluation( self, operation, dataflow ):
		return self._flow(operation.getEvaluable())

	def flowImportOperation( self, operation, dataflow):
		self.stage2.append((self._flowImportOperationStage2, (operation, dataflow)))

	def _importedAbsoluteName( self, to_resolve ):
		if not to_resolve: return []
		res = self._importedAbsoluteName(to_resolve.getContext())
		res.append(to_resolve.getReference().getReferenceName())
		return res

	def _flowImportOperationStage2( self, program, operation, dataflow):
		#FIXME: Thiss is a hack, should use getCurrentModule instead
		current_module = dataflow.parents[0].element
		dataflow       = current_module.getDataFlow()
		if isinstance( operation, interfaces.IImportSymbolOperation):
			import_origin = operation.getImportOrigin()
			imported_element = operation.getImportedElement()
			imported_alias = operation.getAlias() or imported_element
			module = program.getModule(import_origin)
			if module:
				df_slot, scope = module.getDataFlow().resolve(imported_element)
				dataflow.declareImported(imported_alias, df_slot.getValue(), module)
			else:
				self.report.error("Resolver: Import operation: module not found: %s" % (import_origin))
				

# EOF
