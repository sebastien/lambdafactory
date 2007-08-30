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
	"""Returns the content of this annotation."""
	def getContent(self):
		pass
	
	"""Returns the name of this annotation."""
	def getName(self):
		pass
	

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
		pass
	
	def getLine(self):
		pass
	
	def getColumn(self):
		pass
	

class IDataFlow:
	"""The DataFlow are ''dynamic contexts'' bound to the various program model
	elements. DataFlows are typically owned by elements which implement
	'IContext', and are linked together by rules @methodined in the 'Resolver'
	@protocol.
	
	The dataflow bound to most expressions is the one of the enclosing closure
	(whether it is a function, or method. The dataflow of a method is bound to
	its parent @protocol, which dataflow is also bound to the parent @protocol dataflow.
	
	While 'DataFlow' and 'Context' may appear very similar, they are not the
	same: contexts are elements that keep track of declared slots, while the
	dataflow make use of the context to weave the elements togeher."""
	def declareArgument(self, name, value):
		pass
	
	"""Declares an environment variable with the given name, value
	and origin."""
	def declareEnvironment(self, name, value):
		pass
	
	"""Declares a (local) variable with the given name, value and
	origin"""
	def declareVariable(self, name, value, origin=None):
		if origin is None: origin = None
		pass
	
	"""Returns the lsit of slots @methodiend for this dataflow."""
	def getSlots(self):
		pass
	
	"""Tells if this dataflow @methodines a slot with the given name."""
	def hasSlot(self, name):
		pass
	
	"""Returns the list of parent dataflows for this dataflow."""
	def getParents(self):
		pass
	
	"""Add the given dataflow as a parent of this dataflow."""
	def addParent(self, parent):
		pass
	
	"""Adds the given dataflow as a child of this dataflow."""
	def addChild(self, child):
		pass
	
	"""Returns a list of the child dataflows for this dataflow."""
	def getChildren(self):
		pass
	
	"""Returns a couple '(DataFlow slot, IElement)' or '(None,None)'
	corresponding to the resolution of the given 'name' in this dataflow."""
	def resolve(self, name):
		pass
	
	"""Tells if this dataflow, or any of its child dataflows defines
	the given name (symbol)"""
	def defines(self, name):
		pass
	
	"""Returns the slot with the given name, if any."""
	def getSlot(self, name):
		pass
	

class IDataFlowSlot:
	def addOperation(self):
		pass
	
	"""Returns the (ordered) list of operations that affected the slot.
	Operations usually constrain the dataflow abstract type, and
	exception/warnings/errors may be raised by the type system
	when a type constraint fails."""
	def getOperations(self):
		pass
	
	def getOrigin(self):
		pass
	
	def getOriginalValue(self):
		pass
	
	def getName(self):
		pass
	
	def getAbstractType(self):
		pass
	

class IDataFlowOwner:
	"""DataFlow owners are elements that have their own dataflow. IContext are
	typical examples of elements that are dataflow owners"""
	pass

class IElement:
	"""The core @protocol for every element."""
	"""Returns the abstract type for this element"""
	def getAbstractType(self):
		pass
	
	"""Sets the abstract type for this element"""
	def setAbstractType(self, type):
		pass
	
	"""Returns the dataflow accessible/bound to this element"""
	def getDataFlow(self):
		pass
	
	"""Gets the annotation with the given name associated to this element"""
	def getAnnotation(self, name):
		pass
	
	"""Sets the annotation with the given name to this element"""
	def setAnnotation(self, name, annotation):
		pass
	

class IReferencable:
	"""A referencable is an element that can be referenced either by id (it is
	unique and stable), or by a name (which is also not supposed to change).
	
	Types are good examples of referencables: they have an *absolute name* (like
	`Data.List`), but can also be bound to slots within contexts which give them
	"local names" (like `List := Data.List`)"""
	"""Returns the local name for this referencable element"""
	def getName(self):
		pass
	
	"""Returns the absolute name for this element"""
	def getAbsoluteName(self):
		pass
	

class IAssignable:
	"""Assignable elements are elements that can be bound to slots. In many
	languages, only a subset of elements can be assigned. For instance, in
	Java, you cannot assign a package to something:
	
	>     Object my_package = java.lang.Object
	
	while in some other languages (like JavaScript), you could do that."""
	pass

class IEvaluable:
	"""An evaluable is an element that can produce a value. Evaluable elements
	then have associated type information."""
	"""Returns the abstract type of the result of the evaluation of this
	evaluable"""
	def getResultAbstractType(self):
		pass
	
	"""Sets the abstract type for this operation result. This is usually
	invoked in the typing phase."""
	def setResultAbstractType(self):
		pass
	

class IInstanciable:
	"""Instanciable is a property of some elements that allows them to be
	instanciated. Conceptually, an instanciation could be considered as a
	specific kind of invocation."""
	pass

class IInvocable:
	"""An invocable can be used in an invocation operation."""
	"""Returns a list of arguments (which are names associated with optional
	type information."""
	def getArguments(self):
		pass
	

class IAbstractable:
	"""An abstractable element is an element that is allow to have
	no underlying implementation.  Abstract element are typically interfaces,
	methods, functions, operations, and sometimes modules and @protocoles."""
	"""Tells wether the given abstractable is abstract or not."""
	def isAbstract(self):
		pass
	
	"""Sets wether the given abstractable is abstract or not."""
	def setAbstract(self, isAbstract):
		pass
	

class IValue(IElement, IEvaluable):
	"""A value represents an atomic element of the language, like a number, a
	string, or a name (that can resolved by the language, acts as key for data
	structures, etc.)."""
	pass

class ILiteral(IValue):
	"""A literal is a value that does not need a context to be evaluated. The
	evaluation is direct."""
	pass

class INumber(ILiteral):
	pass

class IString(ILiteral):
	pass

class IList(IValue):
	"""Adds a value to this list."""
	def addValue(self, value):
		pass
	
	"""Returns the values within this list."""
	def getValues(self):
		pass
	

class IDict(IValue):
	"""A dictionary is a binding of key to values. It may or may not be ordered,
	depending on the implementation/model semantics."""
	"""Sets the value to be associated to the given key (which must be an
	evaluable)."""
	def setValue(self, key, value):
		pass
	
	"""Returns the items contained in this dict"""
	def getItems(self):
		pass
	

class IReference(IValue, IReferencable):
	"""A reference is a name that can be converted into a value using a
	resolution operation (for instance)."""
	"""Returns the name which this reference contains. The name is used by
	the resolution operation to actually resolve a value from the name."""
	def getReferenceName(self):
		pass
	

class IOperator(IReference):
	"""Sets the priority for this operator"""
	def setPriority(self, priority):
		pass
	
	"""Gets the priority for this operator"""
	def getPriority(self):
		pass
	

class ISlot(IReference):
	"""An argument is a reference with additional type information."""
	"""Returns type information (constraints) that are associated to this
	argument."""
	def getTypeInformation(self):
		pass
	

class IArgument(ISlot):
	"""Arguments are slots which can be interpreted in different ways.
	
	When an argument is _optional_, it does not need to be @methodined in the
	invocation. When an argument is _variable_, it means it references the
	rest of the arguments lists. When an argument is _keywords_, it will reference
	the named arguments of the rest of the arguments list."""
	"""Tells if the argument is optional or not."""
	def isOptional(self):
		pass
	
	"""Sets this argument as optional or not."""
	def setOptional(self, value):
		pass
	
	"""Tells if the argument is variable or not."""
	def isRest(self):
		pass
	
	"""Sets this argument as variable or not."""
	def setRest(self, value):
		pass
	
	"""Tells if the argument is keywords list or not."""
	def isKeywords(self):
		pass
	
	"""Sets this argument as keywords list  or not."""
	def setKeywords(self, value):
		pass
	
	"""Sets the @methodault value for this argument."""
	def setDefaultValue(self, value):
		pass
	
	"""Returns the @methodault value for this slot."""
	def getDefaultValue(self):
		pass
	

class IAttribute(ISlot):
	"""Sets the @methodault value for this attribute"""
	def setDefaultValue(self):
		pass
	
	"""Gets the @methodault value for this attribute"""
	def getDefaultValue(self):
		pass
	

class IModuleAttribute(IAttribute):
	pass

class IClassAttribute(IAttribute):
	pass

class IContext(IElement, IDataFlowOwner):
	"""A context is an element that has slots, which bind evaluable elements
	(aka values) to names."""
	"""Binds the given evaluable to the named slot."""
	def setSlot(self, name, evaluable):
		pass
	
	"""Returns the given evaluable bound to named slot."""
	def getSlot(self, name):
		pass
	
	"""Tells if the context has a slot with the given name."""
	def hasSlot(self, name):
		pass
	
	"""Returns (key, evaluable) pairs representing the slots within this
	context."""
	def getSlots(self):
		pass
	
	"""Sets the parent context for this context."""
	def setParent(self, context):
		pass
	
	"""Returns the parent context for this context (if any)"""
	def getParent(self):
		pass
	

class IClass(IContext, IReferencable):
	"""Returns the (non-@protocol) attributes @methodined within this @protocol."""
	def getAttributes(self):
		pass
	
	"""Returns the @protocol attributes @methodined within this @protocol."""
	def getClassAttributes(self):
		pass
	
	"""Returns the operations (methods and @protocol methods) @methodined within this @protocol."""
	def getOperations(self):
		pass
	
	"""Returns the methods @methodined within this @protocol."""
	def getMethods(self):
		pass
	
	"""Returns the constructors for this @protocol"""
	def getConstructors(self):
		pass
	
	"""Returns the destructors for this @protocol"""
	def getDestructors(self):
		pass
	
	"""Returns the instance methods @methodined within this @protocol."""
	def getInstanceMethods(self):
		pass
	
	"""Returns the @protocol method @methodined within this @protocol."""
	def getClassMethods(self):
		pass
	
	"""Returns this @protocol name. It can be `None` if the @protocol is anonymous."""
	def getName(self):
		pass
	
	"""Returns the list of inherited @protocoles references."""
	def getSuperClasses(self):
		pass
	

class IAbstractClass(IClass, IAbstractable):
	"""An abstract @protocol is a @protocol that has at least one abstract element."""
	pass

class IInterface(IAbstractClass):
	"""An interface is an abstract @protocol that only has abstract elements."""
	pass

class IModule(IContext):
	def getClasses(self):
		pass
	

class IProgram(IContext):
	"""The program is the core context and entry point for almost every
	operation offered by LambdaFactory."""
	pass

class IProcess:
	"""A process is a sequence of operations."""
	"""Adds the given operation as a child of this process."""
	def addOperation(self, operation):
		pass
	
	"""Adds the given operations as children of this process."""
	def addOperations(self, operations):
		pass
	
	"""Returns the list of operations in this process."""
	def getOperations(self):
		pass
	

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
		pass
	
	def setArguments(self):
		pass
	

class IFunction(IClosure, IReferencable, IAbstractable):
	"""Returns this @protocol name. It can be `None` if the @protocol is anonymous."""
	def getName(self):
		pass
	
	"""Returns true if this function has an operation with a termination,
	otherwise return false."""
	def hasExplicitTermination(self):
		pass
	
	"""Returns true if this function ends with a termination operation. This
	is especially useful for back-ends which want to know if they have to
	insert an explicit 'return' at the end (like Java)."""
	def endsWithTermination(self):
		pass
	

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
	"""Adds an argument to this operation. This should do checking of
	arguments (by expected internal type and number)."""
	def addOpArgument(self, argument):
		pass
	
	"""Returns the arguments to this operation."""
	def getOpArguments(self):
		pass
	
	"""Returns the ith arguments to this operation."""
	def getOpArgument(self, i):
		pass
	
	"""Sets the given argument of this operation, by argument index."""
	def setOpArgument(self, i, value):
		pass
	
	"""Returns the *internal types* for this operations arguments. This is
	typically the list of interfaces or @protocols that the arguments must
	comply to."""
	def getOpArgumentsInternalTypes(self):
		pass
	

class IImportOperation(IOperation):
	ARGS = [IEvaluable, IEvaluable]
	ARG_NAMES = ["ImportedElement", "Alias"]
	"""Returns a reference or a resolution that will allow to get the
	imported element."""
	def getImportedElement(self):
		return self.getOpArgument(0)
	
	"""Returns the (optional) alias which will allow to reference the
	element."""
	def getAlias(self):
		return self.getOpArgument(1)
	

class IEvaluation(IOperation):
	ARGS = [IEvaluable, IEvaluable]
	ARG_NAMES = ["Evaluable"]
	def getEvaluable(self):
		return self.getOpArgument(0)
	

class IAssignation(IOperation):
	ARGS = [IEvaluable, IEvaluable]
	"""Returns this assignation target reference, which can be an evaluable
	(in case you assign to self.something, or a reference)"""
	def getTarget(self):
		pass
	
	"""Returns this assigned evaluable."""
	def getAssignedValue(self):
		pass
	

class IAllocation(IOperation):
	ARGS = [ISlot, IEvaluable]
	"""Returns slot to be allocated by this operation."""
	def getSlotToAllocate(self):
		pass
	
	"""Returns the expression that assigns the @methodault value."""
	def getDefaultValue(self):
		pass
	

class IResolution(IOperation):
	"""A resolution resolves a reference into a value."""
	ARGS = [IReferencable, IEvaluable]
	"""Returns the reference to be resolved."""
	def getReference(self):
		pass
	
	"""Returns the (optional) context in which the resolution should occur."""
	def getContext(self):
		pass
	

class IComputation(IOperation):
	ARGS = [IOperator, IEvaluable, IEvaluable]
	"""Gets the operator for this computation"""
	def getOperator(self):
		return self.getOpArgument(0)
	
	"""Sets the operator for this computation"""
	def setOperator(self, operator):
		return self.getOpArgument(0, operator)
	
	"""Returns the left operand of this computation."""
	def getOperand(self):
		return self.getLeftOperand()
	
	"""Returns the left (and right, if any) operands of this computation."""
	def getOperands(self):
		return [self.getLeftOperand(), self.getRightOperand()]
	
	"""Returns the left operand of this computation."""
	def getLeftOperand(self):
		return self.getOpArgument(1)
	
	"""Returns the right operand of this computation (if any)"""
	def getRightOperand(self):
		return self.getOpArgument(2)
	
	"""Sets the left operand of this computation."""
	def setLeftOperand(self, operand):
		return self.setOpArgument(1, operand)
	
	"""Sets the right operand of this computation"""
	def setRightOperand(self, operand):
		return self.setOpArgument(2, operand)
	

class IInvocation(IOperation):
	ARGS = [IEvaluable, [IEvaluable]]
	"""Returns the invocation target reference."""
	def getTarget(self):
		return self.getOpArgument(0)
	
	"""Returns evaluable arguments."""
	def getArguments(self):
		return self.getOpArgument(1)
	

class IInstanciation(IOperation):
	ARGS = [IEvaluable, [IEvaluable]]
	"""Returns the instanciable used in this operation."""
	def getInstanciable(self):
		return self.getOpArgument(0)
	
	"""Returns evaluable arguments."""
	def getArguments(self):
		return self.getOpArgument(1)
	

class ISubsetOperation(IOperation):
	"""Returns the operation target."""
	def getTarget(self):
		return self.getOpArgument(0)
	

class IAccessOperation(ISubsetOperation):
	ARGS = [IEvaluable, IEvaluable]
	"""Returns evaluable that will return the access index"""
	def getIndex(self):
		return self.getOpArgument(1)
	

class ISliceOperation(ISubsetOperation):
	ARGS = [IEvaluable, IEvaluable, IEvaluable]
	"""Returns evaluable that will return the slice start"""
	def getSliceStart(self):
		return self.getOpArgument(1)
	
	"""Returns evaluable that will return the slice end"""
	def getSliceEnd(self):
		return self.getOpArgument(2)
	

class IMatchOperation(IOperation):
	"""A match operation is the binding of an expression and a process."""
	"""Returns the evaluable that acts as a predicate for this operation."""
	def getPredicate(self):
		return self.getOpArgument(0)
	
	def setPredicate(self, v):
		return self.setOpArgument(0, v)
	

class IMatchExpressionOperation(IMatchOperation):
	"""A match expression is a predicate that is associated to an expression.
	This is typically used in conditional expressions like in C:
	
	>	int a = ( b==2 ? 1 : 2 )"""
	ARGS = [IEvaluable, IEvaluable]
	"""Returns the process that will be executed if the rule matches."""
	def getExpression(self):
		return self.getOpArgument(1)
	
	def setExpression(self, v):
		return self.setOpArgument(1, v)
	

class IMatchProcessOperation(IMatchOperation):
	"""A match process is a predicate associate to a process, which is typically
	used for implementing 'if', 'else', etc."""
	ARGS = [IEvaluable, IProcess]
	"""Returns the process that will be executed if the rule matches."""
	def getProcess(self):
		return self.getOpArgument(1)
	
	def setProcess(self, v):
		return self.setOpArgument(1, v)
	

class ISelection(IOperation):
	"""Selections are the abstract objects behind `if`, `select` or
	pattern-matching operations. Each selection has match operations as
	arguments, which bind a subprocess to a predicate expression."""
	ARGS = [[IMatchOperation]]
	"""Adds a rule to this operation."""
	def addRule(self, evaluable):
		pass
	
	"""Returns the ordered set of rule for this selection."""
	def getRules(self):
		pass
	

class IIteration(IOperation):
	"""An iteration is the multiple application of a process given a set of
	values produced by an iterator."""
	ARGS = [IEvaluable, IEvaluable]
	"""Returns this iteration iterator."""
	def getIterator(self):
		return self.getOpArgument(0)
	
	"""Returns the closure that will be applied to the iterator."""
	def getClosure(self):
		return self.getOpArgument(1)
	

class IEnumeration(IOperation):
	"""An enumeration produces values between a start and an end value, with the
	given step."""
	ARGS = [IEvaluable, IEvaluable, IEvaluable]
	"""Returns this enumeration start."""
	def getStart(self):
		return self.getOpArgument(0)
	
	"""Returns this enumeration end."""
	def getEnd(self):
		return self.getOpArgument(1)
	
	"""Returns this enumeration step."""
	def getStep(self):
		return self.getOpArgument(2)
	
	"""Sets this enumeration step"""
	def setStep(self, value):
		return self.setOpArgument(2, value)
	

class IRepetition(IOperation):
	"""A repetition is the repetitive execution of a process according to a
	predicate expression which can be modified by the process."""
	ARGS = [IEvaluable, IProcess]
	"""Gets the expression that is the condition for this repetition."""
	def getCondition(self):
		return self.getOpArgument(0)
	
	def getProcess(self):
		return self.getOpArgument(1)
	

class ITermination(IOperation):
	ARGS = [IEvaluable]
	"""Returns the termination return evaluable."""
	def getReturnedEvaluable(self):
		pass
	

class IInterruption(IOperation):
	"""An interruption can be be used to halt the process."""
	pass

class IBreaking(IInterruption):
	ARGS = []

class IExcept(IInterruption):
	"""An interruption that raises some value"""
	ARGS = [IEvaluable]
	"""Returns the termination return evaluable."""
	def getValue(self):
		return self.getOpArgument(0)
	

class IInterception(IOperation):
	"""An interception allows to intercept interruptions that propagage from an
	enclosed process to parent contexts."""
	ARGS = [IProcess, IProcess, IProcess]
	"""Sets the process from which interruptions will be intercepted."""
	def setProcess(self, process):
		return self.setOpArgument(0, process)
	
	"""Returns the process that we will intercept interruptions from."""
	def getProcess(self):
		return self.getOpArgument(0)
	
	"""Sets the process that will do the interception"""
	def setIntercept(self, process):
		return self.setOpArgument(1, process)
	
	"""Returns the process that will do the interception"""
	def getIntercept(self):
		return self.getOpArgument(1)
	
	"""Sets the process that will conclude the interception (finally)"""
	def setConclusion(self, process):
		return self.setOpArgument(2, process)
	
	"""Returns the process that will conclude the interception (finally)"""
	def getConclusion(self):
		return self.getOpArgument(2)
	

class IEmbed(IOperation):
	"""An embedded operation represents a bit of verbatim code written in
	a different language. This allows for embedding code written specifically
	in a target language (which may happen for optimizing stuff, for instance)."""
	ARGS = []
	"""Returns the language in which the emebedded code is written."""
	def getLanguage(self):
		pass
	
	"""Sets the language in which the emebedded code is written."""
	def setLanguage(self, language):
		pass
	
	"""Returns the embedded code string."""
	def getCodeString(self):
		pass
	
	"""Sets the code of this embed operation."""
	def setCodeString(self, code):
		pass
	

class IEmbedTemplate(IEmbed):
	"""The 'EmbedTemplate' is embedded ('Embed') that contains template
	expressions. It's up to the model writer to know how to expand the template
	to convert it to the target language."""
	pass

