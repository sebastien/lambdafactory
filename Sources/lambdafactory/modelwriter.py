import interfaces

__doc__ = """
The *model writer* modules define a default program model to text conversion
class and a set of useful functions to help writing program model to text
translators.

Model writers can be used to convert a program model to source code in a
specific language. As writer are stateful, you can add many checkings and
transformations while writing a program, or parts of it.
"""

PREFIX = "\t"

def _format( value, level=-1 ):
	"""Format helper operation. See @format."""
	if type(value) in (list, tuple):
		res = []
		for v in value:
			if v is None: continue
			res.extend(_format(v, level+1))
		return res
	else:
		assert type(value) in (str, unicode), "Unsupported type: %s" % (value)
		return ["\n".join((level*PREFIX)+v for v in value.split("\n"))]

def format( *values ):
	"""Formats a combination of string ang tuples. Strings are joined by
	newlines, and the content of the inner tuples gets indented"""
	return "\n".join(_format(values))

def _flatten(value, res):
	"""Flatten helper operation. See @flatten."""
	if type(value) in (tuple, list):
		for v in value:
			_flatten(v, res)
	else:
		res.append(value)

def flatten( *lists ):
	"""Flattens the given lists in a single list."""
	res = [] ; _flatten(lists, res)
	return res

class Writer:
	"""This is the default writer implementation that outputs a text-based
	program representation. You can call the main @write method to get the
	representatio of any model element."""

	# This defines an ordered set of interfaces names (without the leading I).
	# This list is used in the the write method
	# NOTE: When adding elements, be sure to put the *particular first*
	INTERFACES = (
		"Module", "Class",
		"ClassMethod", "Method", "Function", "Block",
		"ClassAttribute", "Attribute", "Argument", "Reference",
		"Operator", "Number", "String",
		"Enumeration",
		"Allocation", "Assignation", "Computation",
		"Invocation", "Resolution", "Selection",
		"Repetition", "Iteration",  "Termination"
	)

	def writeModule( self, moduleElement ):
		"""Writes a Module element."""
		return self._format("module %s:" % (moduleElement.getName()),
			[self.write(s[1]) for s in moduleElement.getSlots()],
			"end"
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		return self._format(
			self._document(classElement),
			"class %s:" % (classElement.getName()),
			flatten([self.write(m) for m in classElement.getAttributes()]),
			flatten([self.write(m) for m in classElement.getClassAttributes()]),
			flatten([self.write(m) for m in classElement.getMethods()]),
			flatten([self.write(m) for m in classElement.getClassMethods()]),
			"end"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		return self._format(
			self._document(methodElement),
			"method %s ( %s ):" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"end"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		return self._format(
			self._document(methodElement),
			"operation %s ( %s ):" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"end"
		)

	def writeFunction( self, function ):
		"""Writes a function element."""
		return self._format(
			self._document(function),
			"function %s ( %s ):" % (
				function.getName(),
				", ".join(map(self.write, function.getArguments()))
			),
			map(self.write, function.getOperations()),
			"end"
		)

	def writeBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			map(self.write, block.getOperations())
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s %s" % (
			(argElement.getTypeInformation() or "any"),
			argElement.getReferenceName(),
		)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		return "attribute %s %s" % (
			(element.getTypeInformation() or "any"),
			element.getReferenceName(),
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		return "class attribute %s %s" % (
			(element.getTypeInformation() or "any"),
			element.getReferenceName(),
		)

	def writeReference( self, element ):
		"""Writes an argument element."""
		return element.getReferenceName()

	def writeOperator( self, operator ):
		"""Writes an operator element."""
		return "%s" % (operator.getReferenceName())

	def writeNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def writeString( self, element ):
		"""Writes a string element."""
		return '"%s"' % (element.getActualValue().replace('"', '\\"'))

	def writeAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		if s.getTypeInformation() is None: return None
		return "%s %s" % (
			s.getTypeInformation(),
			s.getReferenceName(),
		)

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			assignation.getTargetReference().getReferenceName(),
			self.write(assignation.getAssignedValue())
		)

	def writeEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart() 
		end   = operation.getStart() 
		if isinstance(start, interfaces.ILitteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILitteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = "%s..%s" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self.write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		return "%s" % ( resolution.getReference().getReferenceName())

	def writeComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = computation.getOperands()
		operator = computation.getOperator()
		if len(operands) == 1:
			return "%s %s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			return "%s %s %s" % (
				self.write(operands[0]),
				self.write(operator),
				self.write(operands[1])
			)

	def writeInvocation( self, invocation ):
		"""Writes an invocation operation."""
		return "%s(%s)" % (
			self.write(invocation.getTarget()),
			", ".join(map(self.write, invocation.getArguments()))
		)

	def writeSelection( self, selection ):
		rules = selection.getRules()
		result = []
		for i in range(0,len(rules)):
			rule = rules[i]
			if i==0:
				rule_code = (
					"if %s:" % (self.write(rule.getPredicate())),
					self.write(rule.getProcess())
				)
			else:
				rule_code = (
					"else if %s:" % (self.write(rule.getPredicate())),
					self.write(rule.getProcess())
				)
			result.extend(rule_code)
		result.append("end")
		return self._format(*result)

	def writeRepetition( self, repetition ):
		return self._format(
			"while %s:" % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess()),
			"end"
		)

	def writeIteration( self, iteration ):
		"""Writes a iteration operation."""
		return self._format(
			"for %s in %s:" % (
				self.write(iteration.getIteratedSlot()),
				self.write(iteration.getIterator())
			),
			self.write(iteration.getProcess()),
			"end"
		)

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def write( self, element ):
		res = None
		if element is None: return ""
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if isinstance(element, the_interface):
				if not hasattr(self, "write" + name ):
					raise Exception("Writer does not define write method for: "
					+ name)
				else:
					return getattr(self, "write" + name)(element)
		raise Exception("Element implements unsupported interface: "
		+ str(element))

	def _format( self, *values ):
		return format(*values)
	
	def _document( self, element ):
		if element.hasDocumentation():
			return "# " + element.getDocumentation()
		else:
			return None

class JSWriter(Writer):

	def writeModule( self, moduleElement ):
		"""Writes a Module element."""
		return self._format("var %s = {" % (moduleElement.getName()),
			[self.write(s[1]) for s in moduleElement.getSlots()],
			"}"
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		return self._format(
			self._document(classElement),
			"%s: Class.create({" % (classElement.getName()),
			flatten([self.write(m) for m in classElement.getAttributes()]),
			flatten([self.write(m) for m in classElement.getClassAttributes()]),
			flatten([self.write(m) for m in classElement.getMethods()]),
			# FIXME
			flatten([self.write(m) for m in classElement.getClassMethods()]),
			"\n\tCLASSDEF:{name:'%s'}" % (classElement.getName()),
			"})"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		return self._format(
			self._document(methodElement),
			"%s: function ( %s ) {" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"},"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		return self._format(
			self._document(methodElement),
			"%s: function ( %s ){" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeFunction( self, function ):
		"""Writes a function element."""
		return self._format(
			self._document(function),
			"function %s ( %s ) {" % (
				function.getName(),
				", ".join(map(self.write, function.getArguments()))
			),
			map(self.write, function.getOperations()),
			"}"
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s" % (
			argElement.getReferenceName(),
		)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		return "%s: undefined," % (
			element.getReferenceName(),
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		return "%s: undefined" % (
			element.getReferenceName(),
		)

	def writeReference( self, element ):
		"""Writes an argument element."""
		return element.getReferenceName()

	def writeOperator( self, operator ):
		"""Writes an operator element."""
		return "%s" % (operator.getReferenceName())

	def writeNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def writeString( self, element ):
		"""Writes a string element."""
		return '"%s"' % (element.getActualValue().replace('"', '\\"'))

	def writeAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		if s.getTypeInformation() is None: return None
		return "var %s" % (
			s.getReferenceName(),
		)

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			assignation.getTargetReference().getReferenceName(),
			self.write(assignation.getAssignedValue())
		)

	def writeEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart() 
		end   = operation.getStart() 
		if isinstance(start, interfaces.ILitteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILitteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = "%s..%s" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self._write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		return "%s" % ( resolution.getReference().getReferenceName())

	def writeComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = computation.getOperands()
		operator = computation.getOperator()
		if len(operands) == 1:
			return "%s %s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			return "%s %s %s" % (
				self.write(operands[0]),
				self.write(operator),
				self.write(operands[1])
			)

	def writeInvocation( self, invocation ):
		"""Writes an invocation operation."""
		return "%s(%s)" % (
			self.write(invocation.getTarget()),
			", ".join(map(self.write, invocation.getArguments()))
		)

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def write( self, element ):
		res = None
		if element is None: return ""
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if isinstance(element, the_interface):
				if not hasattr(self, "write" + name ):
					raise Exception("Writer does not define write method for: "
					+ name)
				else:
					return getattr(self, "write" + name)(element)
		raise Exception("Element implements unknown interface: "
		+ str(element))

	def _format( self, *values ):
		return format(*values)
	
	def _document( self, element ):
		if element.hasDocumentation():
			return "# " + element.getDocumentation()
		else:
			return None

# EOF
