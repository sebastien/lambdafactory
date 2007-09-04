#8< ---[interfaces.py]---
import sys
__module__ = sys.modules[__name__]
__module_name__ = 'interfaces'
class Constants:
	MainFunction = "__main__"
	CurrentModule = "__current__"
	Constructor = "__init__"
	Destructor = "__destroy__"
	ModuleInit = "__moduleinit__"
	CurrentValue = "__currentvalue__"
	PARENS_PRIORITY = 9999

class IAnnotation:
	"""An annotation is some information that is not used for the actual
	program, but annotates/gives meta-information about is elements."""
	def getContent(self):
		"""Returns the content of this annotation."""
		raise Exception("Abstract method IAnnotation.getContent not implemented")
	
	def getName(self):
		"""Returns the name of this annotation."""
		raise Exception("Abstract method IAnnotation.getName not implemented")
	

class IComment(IAnnotation):
	"""A comment is an annotation that can occur anywhere in a source file."""
	pass

class IDocumentation(IAnnotation):
	"""Documentation is often attached to various language elements.
	Documentation can be found in coments (as in Java), or be directly embedded
	as values (as in Python)."""
	pass

class ISyntactic:
	def getOffset(self):
		raise Exception("Abstract method ISyntactic.getOffset not implemented")
	
	def getLine(self):
		raise Exception("Abstract method ISyntactic.getLine not implemented")
	
	def getColumn(self):
		raise Exception("Abstract method ISyntactic.getColumn not implemented")
	

class IDataFlow:
	"""The DataFlow are ''dynamic contexts'' bound to the various program model
	elements. DataFlows are typically owned by elements which implement
	'IContext', and are linked together by rules defined in the 'Resolver'
	@protocol.
	
	The dataflow bound to most expressions is the one of the enclosing closure
	(whether it is a function, or method. The dataflow of a method is bound to
	its parent @protocol, which dataflow is also bound to the parent @protocol dataflow.
	
	While 'DataFlow' and 'Context' may appear very similar, they are not the
	same: contexts are elements that keep track of declared slots, while the
	dataflow make use of the context to weave the elements togeher."""
	def declareArgument(self, name, value):
		raise Exception("Abstract method IDataFlow.declareArgument not implemented")
	
	def declareEnvironment(self, name, value):
		"""Declares an environment variable with the given name, value
		and origin."""
		raise Exception("Abstract method IDataFlow.declareEnvironment not implemented")
	
	def declareVariable(self, name, value, origin=None):
		"""Declares a (local) variable with the given name, value and
		origin"""
		if origin is None: origin = None
		raise Exception("Abstract method IDataFlow.declareVariable not implemented")
	
	def getSlots(self):
		"""Returns the lsit of slots @methodiend for this dataflow."""
		raise Exception("Abstract method IDataFlow.getSlots not implemented")
	
	def hasSlot(self, name):
		"""Tells if this dataflow @methodines a slot with the given name."""
		raise Exception("Abstract method IDataFlow.hasSlot not implemented")
	
	def getParents(self):
		"""Returns the list of parent dataflows for this dataflow."""
		raise Exception("Abstract method IDataFlow.getParents not implemented")
	
	def addParent(self, parent):
		"""Add the given dataflow as a parent of this dataflow."""
		raise Exception("Abstract method IDataFlow.addParent not implemented")
	
	def addChild(self, child):
		"""Adds the given dataflow as a child of this dataflow."""
		raise Exception("Abstract method IDataFlow.addChild not implemented")
	
	def getChildren(self):
		"""Returns a list of the child dataflows for this dataflow."""
		raise Exception("Abstract method IDataFlow.getChildren not implemented")
	
	def resolve(self, name):
		"""Returns a couple '(DataFlow slot, IElement)' or '(None,None)'
		corresponding to the resolution of the given 'name' in this dataflow."""
		raise Exception("Abstract method IDataFlow.resolve not implemented")
	
	def defines(self, name):
		"""Tells if this dataflow, or any of its child dataflows defines
		the given name (symbol)"""
		raise Exception("Abstract method IDataFlow.defines not implemented")
	
	def getSlot(self, name):
		"""Returns the slot with the given name, if any."""
		raise Exception("Abstract method IDataFlow.getSlot not implemented")
	

class IDataFlowSlot:
	def addOperation(self):
		raise Exception("Abstract method IDataFlowSlot.addOperation not implemented")
	
	def getOperations(self):
		"""Returns the (ordered) list of operations that affected the slot.
		Operations usually constrain the dataflow abstract type, and
		exception/warnings/errors may be raised by the type system
		when a type constraint fails."""
		raise Exception("Abstract method IDataFlowSlot.getOperations not implemented")
	
	def getOrigin(self):
		raise Exception("Abstract method IDataFlowSlot.getOrigin not implemented")
	
	def getOriginalValue(self):
		raise Exception("Abstract method IDataFlowSlot.getOriginalValue not implemented")
	
	def getName(self):
		raise Exception("Abstract method IDataFlowSlot.getName not implemented")
	
	def getAbstractType(self):
		raise Exception("Abstract method IDataFlowSlot.getAbstractType not implemented")
	

class IDataFlowOwner:
	"""DataFlow owners are elements that have their own dataflow. IContext are
	typical examples of elements that are dataflow owners"""
	pass

class IElement:
	"""The core @protocol for every element."""
	def getAbstractType(self):
		"""Returns the abstract type for this element"""
		raise Exception("Abstract method IElement.getAbstractType not implemented")
	
	def setAbstractType(self, type):
		"""Sets the abstract type for this element"""
		raise Exception("Abstract method IElement.setAbstractType not implemented")
	
	def getDataFlow(self):
		"""Returns the dataflow accessible/bound to this element"""
		raise Exception("Abstract method IElement.getDataFlow not implemented")
	
	def getAnnotation(self, name):
		"""Gets the annotation with the given name associated to this element"""
		raise Exception("Abstract method IElement.getAnnotation not implemented")
	
	def setAnnotation(self, name, annotation):
		"""Sets the annotation with the given name to this element"""
		raise Exception("Abstract method IElement.setAnnotation not implemented")
	

class IAssignable:
	"""Assignable elements are elements that can be bound to slots. In many
	languages, only a subset of elements can be assigned. For instance, in
	Java, you cannot assign a package to something:
	
	>     Object my_package = java.lang.Object
	
	while in some other languages (like JavaScript), you could do that."""
	pass

class IReferencable(IAssignable):
	"""A referencable is an element that can be referenced either by id (it is
	unique and stable), or by a name (which is also not supposed to change).
	
	Types are good examples of referencables: they have an *absolute name* (like
	`Data.List`), but can also be bound to slots within contexts which give them
	"local names" (like `List := Data.List`)"""
	def getName(self):
		"""Returns the local name for this referencable element"""
		raise Exception("Abstract method IReferencable.getName not implemented")
	
	def getAbsoluteName(self):
		"""Returns the absolute name for this element"""
		raise Exception("Abstract method IReferencable.getAbsoluteName not implemented")
	

class IEvaluable:
	"""An evaluable is an element that can produce a value. Evaluable elements
	then have associated type information."""
	def getResultAbstractType(self):
		"""Returns the abstract type of the result of the evaluation of this
		evaluable"""
		raise Exception("Abstract method IEvaluable.getResultAbstractType not implemented")
	
	def setResultAbstractType(self, abstractType):
		"""Sets the abstract type for this operation result. This is usually
		invoked in the typing phase."""
		raise Exception("Abstract method IEvaluable.setResultAbstractType not implemented")
	

class IInstanciable:
	"""Instanciable is a property of some elements that allows them to be
	instanciated. Conceptually, an instanciation could be considered as a
	specific kind of invocation."""
	pass

class IInvocable:
	"""An invocable can be used in an invocation operation."""
	def getArguments(self):
		"""Returns a list of arguments (which are names associated with optional
		type information."""
		raise Exception("Abstract method IInvocable.getArguments not implemented")
	

class IAbstractable:
	"""An abstractable element is an element that is allow to have
	no underlying implementation.  Abstract element are typically interfaces,
	methods, functions, operations, and sometimes modules and @protocoles."""
	def isAbstract(self):
		"""Tells wether the given abstractable is abstract or not."""
		raise Exception("Abstract method IAbstractable.isAbstract not implemented")
	
	def setAbstract(self, isAbstract):
		"""Sets wether the given abstractable is abstract or not."""
		raise Exception("Abstract method IAbstractable.setAbstract not implemented")
	

class IValue(IElement, IEvaluable):
	"""A value represents an atomic element of the language, like a number, a
	string, or a name (that can resolved by the language, acts as key for data
	structures, etc.)."""
	pass

class ILiteral(IValue):
	"""A literal is a value that does not need a context to be evaluated. The
	evaluation is direct."""
	def getActualValue(self):
		"""Returns the (implementation language) value for this literal"""
		raise Exception("Abstract method ILiteral.getActualValue not implemented")
	

class INumber(ILiteral):
	pass

class IString(ILiteral):
	pass

class IList(IValue):
	def addValue(self, value):
		"""Adds a value to this list."""
		raise Exception("Abstract method IList.addValue not implemented")
	
	def getValues(self):
		"""Returns the values within this list."""
		raise Exception("Abstract method IList.getValues not implemented")
	

class IDict(IValue):
	"""A dictionary is a binding of key to values. It may or may not be ordered,
	depending on the implementation/model semantics."""
	def setValue(self, key, value):
		"""Sets the value to be associated to the given key (which must be an
		evaluable)."""
		raise Exception("Abstract method IDict.setValue not implemented")
	
	def getItems(self):
		"""Returns the items contained in this dict"""
		raise Exception("Abstract method IDict.getItems not implemented")
	

class IReference(IValue, IReferencable):
	"""A reference is a name that can be converted into a value using a
	resolution operation (for instance)."""
	def getReferenceName(self):
		"""Returns the name which this reference contains. The name is used by
		the resolution operation to actually resolve a value from the name."""
		raise Exception("Abstract method IReference.getReferenceName not implemented")
	

class IOperator(IReference):
	def setPriority(self, priority):
		"""Sets the priority for this operator"""
		raise Exception("Abstract method IOperator.setPriority not implemented")
	
	def getPriority(self):
		"""Gets the priority for this operator"""
		raise Exception("Abstract method IOperator.getPriority not implemented")
	

class ISlot(IReferencable):
	"""An argument is a reference with additional type information."""
	def getTypeDescription(self):
		"""Returns type information (constraints) that are associated to this
		argument."""
		raise Exception("Abstract method ISlot.getTypeDescription not implemented")
	

class IArgument(ISlot):
	"""Arguments are slots which can be interpreted in different ways.
	
	When an argument is _optional_, it does not need to be defined in the
	invocation. When an argument is _variable_, it means it references the
	rest of the arguments lists. When an argument is _keywords_, it will reference
	the named arguments of the rest of the arguments list."""
	def isOptional(self):
		"""Tells if the argument is optional or not."""
		raise Exception("Abstract method IArgument.isOptional not implemented")
	
	def setOptional(self, value):
		"""Sets this argument as optional or not."""
		raise Exception("Abstract method IArgument.setOptional not implemented")
	
	def isRest(self):
		"""Tells if the argument is variable or not."""
		raise Exception("Abstract method IArgument.isRest not implemented")
	
	def setRest(self, value):
		"""Sets this argument as variable or not."""
		raise Exception("Abstract method IArgument.setRest not implemented")
	
	def isKeywords(self):
		"""Tells if the argument is keywords list or not."""
		raise Exception("Abstract method IArgument.isKeywords not implemented")
	
	def setKeywords(self, value):
		"""Sets this argument as keywords list  or not."""
		raise Exception("Abstract method IArgument.setKeywords not implemented")
	
	def setDefaultValue(self, value):
		"""Sets the @methodault value for this argument."""
		raise Exception("Abstract method IArgument.setDefaultValue not implemented")
	
	def getDefaultValue(self):
		"""Returns the @methodault value for this slot."""
		raise Exception("Abstract method IArgument.getDefaultValue not implemented")
	

class IAttribute(ISlot):
	def setDefaultValue(self):
		"""Sets the @methodault value for this attribute"""
		raise Exception("Abstract method IAttribute.setDefaultValue not implemented")
	
	def getDefaultValue(self):
		"""Gets the @methodault value for this attribute"""
		raise Exception("Abstract method IAttribute.getDefaultValue not implemented")
	

class IModuleAttribute(IAttribute):
	pass

class IClassAttribute(IAttribute):
	pass

class IContext(IElement, IDataFlowOwner):
	"""A context is an element that has slots, which bind evaluable elements
	(aka values) to names."""
	def setSlot(self, name, evaluable):
		"""Binds the given evaluable to the named slot."""
		raise Exception("Abstract method IContext.setSlot not implemented")
	
	def getSlot(self, name):
		"""Returns the given evaluable bound to named slot."""
		raise Exception("Abstract method IContext.getSlot not implemented")
	
	def hasSlot(self, name):
		"""Tells if the context has a slot with the given name."""
		raise Exception("Abstract method IContext.hasSlot not implemented")
	
	def getSlots(self):
		"""Returns (key, evaluable) pairs representing the slots within this
		context."""
		raise Exception("Abstract method IContext.getSlots not implemented")
	
	def setParent(self, context):
		"""Sets the parent context for this context."""
		raise Exception("Abstract method IContext.setParent not implemented")
	
	def getParent(self):
		"""Returns the parent context for this context (if any)"""
		raise Exception("Abstract method IContext.getParent not implemented")

class IClass(IContext, IReferencable):
	def setParentClasses(self):
		"""gives the list of parent classes that will"""
		raise Exception("Abstract method IClass.setParentClasses not implemented")
	
	def getAttributes(self):
		"""Returns the (non-class) attributes defined within this class."""
		raise Exception("Abstract method IClass.getAttributes not implemented")
	
	def getClassAttributes(self):
		"""Returns the class attributes defined within this class."""
		raise Exception("Abstract method IClass.getClassAttributes not implemented")
	
	def getOperations(self):
		"""Returns the operations (methods and class methods) defined within this class."""
		raise Exception("Abstract method IClass.getOperations not implemented")
	
	def getMethods(self):
		"""Returns the methods defined within this class."""
		raise Exception("Abstract method IClass.getMethods not implemented")
	
	def getConstructors(self):
		"""Returns the constructors for this class"""
		raise Exception("Abstract method IClass.getConstructors not implemented")
	
	def getDestructors(self):
		"""Returns the destructors for this class"""
		raise Exception("Abstract method IClass.getDestructors not implemented")
	
	def getInstanceMethods(self):
		"""Returns the instance methods defined within this class."""
		raise Exception("Abstract method IClass.getInstanceMethods not implemented")
	
	def getClassMethods(self):
		"""Returns the class method defined within this class."""
		raise Exception("Abstract method IClass.getClassMethods not implemented")
	
	def getName(self):
		"""Returns this class name. It can be `None` if the class is anonymous."""
		raise Exception("Abstract method IClass.getName not implemented")
	
	def getParentClasses(self):
		"""Returns the list of inherited classes references."""
		raise Exception("Abstract method IClass.getParentClasses not implemented")
	

class IAbstractClass(IClass, IAbstractable):
	"""An abstract @protocol is a @protocol that has at least one abstract element."""
	pass

class IInterface(IAbstractClass):
	"""An interface is an abstract @protocol that only has abstract elements."""
	pass

class IModule(IContext):
	def getClasses(self):
		"""Returns the list of classes defined in this module. This is mainly a
		convenience function."""
		raise Exception("Abstract method IModule.getClasses not implemented")
	

class IProgram(IContext):
	"""The program is the core context and entry point for almost every
	operation offered by LambdaFactory."""
	def addModule(self, module):
		"""Adds a module to this program. The module will be registered in
		the global module catalogue."""
		raise Exception("Abstract method IProgram.addModule not implemented")
	
	def getModule(self, moduleAbsoluteName):
		"""Returns the module (if any) with the given absolute name"""
		raise Exception("Abstract method IProgram.getModule not implemented")
	
	def setFactory(self, factory):
		"""Sets the factory that was used to create this program"""
		raise Exception("Abstract method IProgram.setFactory not implemented")
	
	def getFactory(self):
		"""Gets the factory that was used to create this program. It can be
		used to create more elements in the program."""
		raise Exception("Abstract method IProgram.getFactory not implemented")
	

class IProcess:
	"""A process is a sequence of operations."""
	def addOperation(self, operation):
		"""Adds the given operation as a child of this process."""
		raise Exception("Abstract method IProcess.addOperation not implemented")
	
	def getOperations(self):
		"""Returns the list of operations in this process."""
		raise Exception("Abstract method IProcess.getOperations not implemented")
	

class IGroup(IProcess):
	"""A block is a group of operations that share a common aspect. Groups
	are more likely to be used by program passes to further structure the
	program.
	
	Groups should generally not have their own context, as opposed to blocks
	which generally have a context of their own."""
	pass

class IBlock(IGroup):
	"""A block is a specific type of (sub) process."""
	pass

class IClosure(IProcess, IContext):
	def getArguments(self):
		raise Exception("Abstract method IClosure.getArguments not implemented")
	
	def setArguments(self):
		raise Exception("Abstract method IClosure.setArguments not implemented")
	

class IFunction(IClosure, IReferencable, IAbstractable):
	def getName(self):
		"""Returns this @protocol name. It can be `None` if the @protocol is anonymous."""
		raise Exception("Abstract method IFunction.getName not implemented")
	
	def hasExplicitTermination(self):
		"""Returns true if this function has an operation with a termination,
		otherwise return false."""
		raise Exception("Abstract method IFunction.hasExplicitTermination not implemented")
	
	def endsWithTermination(self):
		"""Returns true if this function ends with a termination operation. This
		is especially useful for back-ends which want to know if they have to
		insert an explicit 'return' at the end (like Java)."""
		raise Exception("Abstract method IFunction.endsWithTermination not implemented")
	

class IMethod(IFunction):
	pass

class IConstructor(IMethod):
	pass

class IDestructor(IMethod):
	pass

class IInstanceMethod(IMethod):
	pass

class IClassMethod(IMethod):
	pass

class IOperation(IElement):
	def addOpArgument(self, argument):
		"""Adds an argument to this operation. This should do checking of
		arguments (by expected internal type and number)."""
		raise Exception("Abstract method IOperation.addOpArgument not implemented")
	
	def getOpArguments(self):
		"""Returns the arguments to this operation."""
		raise Exception("Abstract method IOperation.getOpArguments not implemented")
	
	def getOpArgument(self, i):
		"""Returns the ith arguments to this operation."""
		raise Exception("Abstract method IOperation.getOpArgument not implemented")
	
	def setOpArgument(self, i, value):
		"""Sets the given argument of this operation, by argument index."""
		raise Exception("Abstract method IOperation.setOpArgument not implemented")
	
	def getOpArgumentsInternalTypes(self):
		"""Returns the *internal types* for this operations arguments. This is
		typically the list of interfaces or @protocols that the arguments must
		comply to."""
		raise Exception("Abstract method IOperation.getOpArgumentsInternalTypes not implemented")
	

class IImportOperation(IOperation):
	pass

class IImportSymbolOperation(IImportOperation):
	ARGS = [IEvaluable, IEvaluable, IEvaluable]
	ARG_NAMES = ["ImportedElement", "ImportOrigin", "Alias"]
	def getImportedElement(self):
		"""Returns a reference or a resolution that will allow to get the
		imported element."""
		return self.getOpArgument(0)
	
	def getImportOrigin(self):
		return self.getOpArgument(1)
	
	def getAlias(self):
		"""Returns the (optional) alias which will allow to reference the
		element."""
		return self.getOpArgument(2)
	

class IImportSymbolsOperation(IImportOperation):
	ARGS = [[IEvaluable], IEvaluable]
	ARG_NAMES = ["ImportedElements", "ImportOrigin"]
	def getImportedElements(self):
		"""Returns a reference or a resolution that will allow to get the
		imported element."""
		return self.getOpArgument(0)
	
	def getImportOrigin(self):
		return self.getOpArgument(1)
	

class IImportModuleOperation(IImportOperation):
	ARGS = [IEvaluable, IEvaluable]
	ARG_NAMES = ["ImportedModuleName", "Alias"]
	def getImportedModuleName(self):
		"""Returns the list of names representing the modules to load"""
		return self.getOpArgument(0)
	
	def getAlias(self):
		return self.getOpArgument(1)
	

class IImportModulesOperation(IImportOperation):
	ARGS = [[IEvaluable]]
	ARG_NAMES = ["ImportedModuleNames"]
	def getImportedModuleNames(self):
		"""Returns the list of names representing the modules to load"""
		return self.getOpArgument(0)
	

class IEvaluation(IOperation):
	ARGS = [IEvaluable, IEvaluable]
	ARG_NAMES = ["Evaluable"]
	def getEvaluable(self):
		return self.getOpArgument(0)
	

class IAssignation(IOperation):
	ARGS = [IEvaluable, IEvaluable]
	def getTarget(self):
		"""Returns this assignation target reference, which can be an evaluable
		(in case you assign to self.something, or a reference)"""
		raise Exception("Abstract method IAssignation.getTarget not implemented")
	
	def getAssignedValue(self):
		"""Returns this assigned evaluable."""
		raise Exception("Abstract method IAssignation.getAssignedValue not implemented")
	

class IAllocation(IOperation):
	ARGS = [ISlot, IEvaluable]
	def getSlotToAllocate(self):
		"""Returns slot to be allocated by this operation."""
		raise Exception("Abstract method IAllocation.getSlotToAllocate not implemented")
	
	def getDefaultValue(self):
		"""Returns the expression that assigns the @methodault value."""
		raise Exception("Abstract method IAllocation.getDefaultValue not implemented")
	

class IResolution(IOperation):
	"""A resolution resolves a reference into a value."""
	ARGS = [IReferencable, IEvaluable]
	def getReference(self):
		"""Returns the reference to be resolved."""
		raise Exception("Abstract method IResolution.getReference not implemented")
	
	def getContext(self):
		"""Returns the (optional) context in which the resolution should occur."""
		raise Exception("Abstract method IResolution.getContext not implemented")
	

class IComputation(IOperation):
	ARGS = [IOperator, IEvaluable, IEvaluable]
	def getOperator(self):
		"""Gets the operator for this computation"""
		return self.getOpArgument(0)
	
	def setOperator(self, operator):
		"""Sets the operator for this computation"""
		return self.getOpArgument(0, operator)
	
	def getOperand(self):
		"""Returns the left operand of this computation."""
		return self.getLeftOperand()
	
	def getOperands(self):
		"""Returns the left (and right, if any) operands of this computation."""
		return [self.getLeftOperand(), self.getRightOperand()]
	
	def getLeftOperand(self):
		"""Returns the left operand of this computation."""
		return self.getOpArgument(1)
	
	def getRightOperand(self):
		"""Returns the right operand of this computation (if any)"""
		return self.getOpArgument(2)
	
	def setLeftOperand(self, operand):
		"""Sets the left operand of this computation."""
		return self.setOpArgument(1, operand)
	
	def setRightOperand(self, operand):
		"""Sets the right operand of this computation"""
		return self.setOpArgument(2, operand)
	

class IInvocation(IOperation):
	ARGS = [IEvaluable, [IEvaluable]]
	def getTarget(self):
		"""Returns the invocation target reference."""
		return self.getOpArgument(0)
	
	def getArguments(self):
		"""Returns evaluable arguments."""
		return self.getOpArgument(1)
	

class IInstanciation(IOperation):
	ARGS = [IEvaluable, [IEvaluable]]
	def getInstanciable(self):
		"""Returns the instanciable used in this operation."""
		return self.getOpArgument(0)
	
	def getArguments(self):
		"""Returns evaluable arguments."""
		return self.getOpArgument(1)
	

class ISubsetOperation(IOperation):
	def getTarget(self):
		"""Returns the operation target."""
		return self.getOpArgument(0)
	

class IAccessOperation(ISubsetOperation):
	ARGS = [IEvaluable, IEvaluable]
	def getIndex(self):
		"""Returns evaluable that will return the access index"""
		return self.getOpArgument(1)
	

class ISliceOperation(ISubsetOperation):
	ARGS = [IEvaluable, IEvaluable, IEvaluable]
	def getSliceStart(self):
		"""Returns evaluable that will return the slice start"""
		return self.getOpArgument(1)
	
	def getSliceEnd(self):
		"""Returns evaluable that will return the slice end"""
		return self.getOpArgument(2)
	

class IMatchOperation(IOperation):
	"""A match operation is the binding of an expression and a process."""
	def getPredicate(self):
		"""Returns the evaluable that acts as a predicate for this operation."""
		return self.getOpArgument(0)
	
	def setPredicate(self, v):
		return self.setOpArgument(0, v)
	

class IMatchExpressionOperation(IMatchOperation):
	"""A match expression is a predicate that is associated to an expression.
	This is typically used in conditional expressions like in C:
	
	>	int a = ( b==2 ? 1 : 2 )"""
	ARGS = [IEvaluable, IEvaluable]
	def getExpression(self):
		"""Returns the process that will be executed if the rule matches."""
		return self.getOpArgument(1)
	
	def setExpression(self, v):
		return self.setOpArgument(1, v)
	

class IMatchProcessOperation(IMatchOperation):
	"""A match process is a predicate associate to a process, which is typically
	used for implementing 'if', 'else', etc."""
	ARGS = [IEvaluable, IProcess]
	def getProcess(self):
		"""Returns the process that will be executed if the rule matches."""
		return self.getOpArgument(1)
	
	def setProcess(self, v):
		return self.setOpArgument(1, v)
	

class ISelection(IOperation):
	"""Selections are the abstract objects behind `if`, `select` or
	pattern-matching operations. Each selection has match operations as
	arguments, which bind a subprocess to a predicate expression."""
	ARGS = [[IMatchOperation]]
	def addRule(self, evaluable):
		"""Adds a rule to this operation."""
		raise Exception("Abstract method ISelection.addRule not implemented")
	
	def getRules(self):
		"""Returns the ordered set of rule for this selection."""
		raise Exception("Abstract method ISelection.getRules not implemented")
	

class IIteration(IOperation):
	"""An iteration is the multiple application of a process given a set of
	values produced by an iterator."""
	ARGS = [IEvaluable, IEvaluable]
	def getIterator(self):
		"""Returns this iteration iterator."""
		return self.getOpArgument(0)
	
	def getClosure(self):
		"""Returns the closure that will be applied to the iterator."""
		return self.getOpArgument(1)
	

class IEnumeration(IOperation):
	"""An enumeration produces values between a start and an end value, with the
	given step."""
	ARGS = [IEvaluable, IEvaluable, IEvaluable]
	def getStart(self):
		"""Returns this enumeration start."""
		return self.getOpArgument(0)
	
	def getEnd(self):
		"""Returns this enumeration end."""
		return self.getOpArgument(1)
	
	def getStep(self):
		"""Returns this enumeration step."""
		return self.getOpArgument(2)
	
	def setStep(self, value):
		"""Sets this enumeration step"""
		return self.setOpArgument(2, value)
	

class IRepetition(IOperation):
	"""A repetition is the repetitive execution of a process according to a
	predicate expression which can be modified by the process."""
	ARGS = [IEvaluable, IProcess]
	def getCondition(self):
		"""Gets the expression that is the condition for this repetition."""
		return self.getOpArgument(0)
	
	def getProcess(self):
		return self.getOpArgument(1)
	

class ITermination(IOperation):
	ARGS = [IEvaluable]
	def getReturnedEvaluable(self):
		"""Returns the termination return evaluable."""
		raise Exception("Abstract method ITermination.getReturnedEvaluable not implemented")
	

class IInterruption(IOperation):
	"""An interruption can be be used to halt the process."""
	pass

class IBreaking(IInterruption):
	ARGS = []

class IExcept(IInterruption):
	"""An interruption that raises some value"""
	ARGS = [IEvaluable]
	def getValue(self):
		"""Returns the termination return evaluable."""
		return self.getOpArgument(0)
	

class IInterception(IOperation):
	"""An interception allows to intercept interruptions that propagage from an
	enclosed process to parent contexts."""
	ARGS = [IProcess, IProcess, IProcess]
	def setProcess(self, process):
		"""Sets the process from which interruptions will be intercepted."""
		return self.setOpArgument(0, process)
	
	def getProcess(self):
		"""Returns the process that we will intercept interruptions from."""
		return self.getOpArgument(0)
	
	def setIntercept(self, process):
		"""Sets the process that will do the interception"""
		return self.setOpArgument(1, process)
	
	def getIntercept(self):
		"""Returns the process that will do the interception"""
		return self.getOpArgument(1)
	
	def setConclusion(self, process):
		"""Sets the process that will conclude the interception (finally)"""
		return self.setOpArgument(2, process)
	
	def getConclusion(self):
		"""Returns the process that will conclude the interception (finally)"""
		return self.getOpArgument(2)
	

class IEmbed(IOperation):
	"""An embedded operation represents a bit of verbatim code written in
	a different language. This allows for embedding code written specifically
	in a target language (which may happen for optimizing stuff, for instance)."""
	ARGS = []
	def getLanguage(self):
		"""Returns the language in which the emebedded code is written."""
		raise Exception("Abstract method IEmbed.getLanguage not implemented")
	
	def setLanguage(self, language):
		"""Sets the language in which the emebedded code is written."""
		raise Exception("Abstract method IEmbed.setLanguage not implemented")
	
	def getCode(self):
		"""Returns the embedded code string."""
		raise Exception("Abstract method IEmbed.getCode not implemented")
	
	def setCode(self, code):
		"""Sets the code of this embed operation."""
		raise Exception("Abstract method IEmbed.setCode not implemented")
	

class IEmbedTemplate(IEmbed):
	"""The 'EmbedTemplate' is embedded ('Embed') that contains template
	expressions. It's up to the model writer to know how to expand the template
	to convert it to the target language."""
	pass

