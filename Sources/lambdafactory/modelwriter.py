#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 08-Jun-2007
# -----------------------------------------------------------------------------

import interfaces, reporter

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
		if value is None: return ""
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

def notEmpty( p ):
	"""Returns None if the given parameter is empty."""
	return p and p or None

class AbstractWriter:

	# This defines an ordered set of interfaces names (without the leading I).
	# This list is used in the the write method
	# NOTE: When adding elements, be sure to put the *particular first*
	INTERFACES = (
		"Module", "Class",
		"Destructor", "Constructor","ClassMethod", "Method", "Function", "Closure", "Block",
		"ClassAttribute", "Attribute", "Argument", "Operator", "Reference",
		"Number", "String", "List", "Dict",
		"Enumeration",
		"Allocation", "Assignation", "Computation",
		"Invocation", "Instanciation", "Resolution", "Selection",
		"Repetition", "Iteration", "AccessOperation", "SliceOperation",
		"Evaluation", "Termination", "ImportOperation"
	)

	def __init__( self, reporter=reporter.DefaultReporter ):
		self._generatedSymbols = {}
		self.contexts = []
		self.report   = reporter

	def _filterContext( self, interface ):
		return filter(lambda x:isinstance(x,interface), self.contexts)

	def getCurrentClosure( self ):
		res = self._filterContext(interfaces.IClosure)
		return res and res[-1] or None

	def getCurrentFunction( self ):
		res = self._filterContext(interfaces.IFunction)
		return res and res[-1] or None

	def getCurrentMethod( self ):
		res = self._filterContext(interfaces.IMethod)
		return res and res[-1] or None

	def isInClassMethod(self):
		return self._filterContext(interfaces.IClassMethod)
	
	def isInInstanceMethod(self):
		return self._filterContext(interfaces.IInstanceMethod)

	def getCurrentClass( self ):
		res = self._filterContext(interfaces.IClass)
		return res and res[-1] or None

	def isIn(self, interface):
		"""Tells wether the current element is in a context where at least one
		of the parent elements define the given interface. It returns '-1'
		when no element implements the interface, and otherwise returns the 
		offset of the element, starting from the most recent context.
		
		To know if you're currently in an assignation:
		>	self.isIn(interfaces.IAssignation)
		"""
		i = len(self.contexts) - 1
		while i >= 0:
			if isinstance(self.contexts[i], interface):
				return i
			i -= 1
		return -1
	
	def getCurrentClassParents( self ):
		res = []
		cur = self.getCurrentClass()
		for ref in cur.getSuperClasses():
			ref = ref.getReferenceName()
			target, context = self.resolve(ref, cur.getDataFlow())
			parent = target.value
			assert parent
			res.append(parent)
		return res
		
	def getCurrentModule( self ):
		res = self._filterContext(interfaces.IModule)
		return res and res[-1] or None

	def getCurrentContext( self ):
		return self.contexts[-1]

	def getCurrentDataFlow( self ):
		i = len(self.contexts) - 1
		while i >= 0:
			if self.contexts[i].hasDataFlow():
				return self.contexts[i].getDataFlow()
			i -= 1
		return None

	def _getContextsAsString( self ):
		res = []
		for c in self.contexts:
			v = c.__class__.__name__
			if hasattr(c,"getName"):
				n = c.getName()
				if n: v += ":" + n
			res.append(v)
		return ".".join(res)

	def resolve( self, name, dataflow=None ):
		current_context = self.contexts[-1]
		if not dataflow: 
			dataflow = self.getCurrentDataFlow()
		if dataflow:
			res = dataflow.resolve(name)
			if not res[0] or not res[1]:
				#raise Exception("Unresolved symbol:" + name )
				self.report.error("Unresolved symbol:" + name, current_context)
			assert len(res) == 2
			return res
		else:
			i = len(self.contexts) - 2
			while i >= 0:
				element = self.contexts[i]
				if isinstance(element, interfaces.IDataFlowable) and \
				element.hasDataFlow():
					return self.resolve(name, element.getDataFlow())
				i -= 1
			raise Exception("No dataflow available in: %s" % (self.contexts))
			return (None,None)

	def write( self, element ):
		res = None
		if element is None: return ""
		if type(element) in (str, unicode): return element
		this_interfaces = [(i,getattr(interfaces,"I" + i)) for i in self.INTERFACES]
		for name, the_interface in this_interfaces:
			if isinstance(element, the_interface):
				if not hasattr(self, "write" + name ):
					raise Exception("Writer does not define write method for: "	+ name)
				else:
					self.contexts.append(element)
					result = getattr(self, "write" + name)(element)
					self.contexts.pop()
					return result
		raise Exception("Element implements unsupported interface: " + str(element))

	def _format( self, *values ):
		return format(*values)
	
	def _document( self, element ):
		if element.hasDocumentation():
			doc = element.getDocumentation()
			res = []
			for line in doc.getContent().split("\n"):
				res.append("| " + line)
			return "\n".join(res)
		else:
			return None


	def _unique( self, name ):
		i = 0
		while True:
			new_name = name + str(i)
			if self._generatedSymbols.get(new_name) == None:
				self._generatedSymbols[new_name] = True
				return new_name
			i+=1

#------------------------------------------------------------------------------
#
#  Default Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):
	"""This is the default writer implementation that outputs a text-based
	program representation. You can call the main @write method to get the
	representatio of any model element."""

	def writeModule( self, moduleElement, contentOnly=False ):
		"""Writes a Module element."""
		return self._format("@module %s" % (moduleElement.getName()),
			[self.write(s[1]) for s in moduleElement.getSlots()],
			"@end"
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		return self._format(
			self._document(classElement),
			"@class %s" % (classElement.getName()),
			flatten([self.write(m) for m in classElement.getAttributes()]),
			flatten([self.write(m) for m in classElement.getClassAttributes()]),
			flatten([self.write(m) for m in classElement.getInstanceMethods()]),
			flatten([self.write(m) for m in classElement.getClassMethods()]),
			"@end"
		)

	def writeDestructor( self, element ):
		"""Writes a method element."""
		return self._format(
			self._document(element),
			"@destructor",
			map(self.write, element.getOperations()),
			"@end"
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		return self._format(
			self._document(element),
			"@constructor %s" % (
				", ".join(map(self.write, element.getArguments()))
			),
			map(self.write, element.getOperations()),
			"@end"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		return self._format(
			self._document(methodElement),
			"@method %s %s" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"@end"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		return self._format(
			self._document(methodElement),
			"@operation %s %s" % (
				methodElement.getName(),
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"@end"
		)

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		return self._format(
			self._document(closure),
			"{%s|" % ( ", ".join(map(self.write, closure.getArguments()))),
			map(self.write, closure.getOperations()),
			"}"
		)

	def writeFunction( self, function ):
		"""Writes a function element."""
		return self._format(
			self._document(function),
			"@function %s %s" % (
				function.getName(),
				", ".join(map(self.write, function.getArguments()))
			),
			map(self.write, function.getOperations()),
			"@end"
		)

	def writeBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			map(self.write, block.getOperations())
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s:%s" % (
			argElement.getReferenceName(),
			(argElement.getTypeInformation() or "any")
		)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		return "@property %s:%s" % (
			element.getReferenceName(),
			(element.getTypeInformation() or "any")
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		return "@shared %s:%s" % (
			element.getReferenceName(),
			(element.getTypeInformation() or "any")
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

	def writeList( self, element ):
		"""Writes a list element."""
		return '[%s]' % (", ".join([
			self.write(e) for e in element.getValues()
		]))

	def writeDict( self, element ):
		return '{%s}' % (", ".join([
			"%s:%s" % ( self.write(k),self.write(v))
			for k,v in element.getItems()
			])
		)

	def writeAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		v = allocation.getDefaultValue()
		if s.getTypeInformation():
			res = "var %s:%s" % (
				s.getReferenceName(),
				s.getTypeInformation()
			)
		else:
			res = "var %s" % (s.getReferenceName())
		if v: res += " = " + self.write(v)
		return res

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			self.write(assignation.getTarget()),
			self.write(assignation.getAssignedValue())
		)

	def writeEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart() 
		end   = operation.getStart() 
		if isinstance(start, interfaces.ILiteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILiteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = "%s..%s" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self.write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		if resolution.getContext():
			return "%s %s" % (self.write(resolution.getContext()), resolution.getReference().getReferenceName())
		else:
			return "%s" % (resolution.getReference().getReferenceName())

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
			return "(%s %s %s)" % (
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
			"while %s" % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess()),
			"end"
		)

	def writeSliceOperation( self, operation ):
		return self._format(
			"%s[%s]" % (self.write(operation.getTarget()), self.write(operation.getSlice()))
		)

	def writeIteration( self, iteration ):
		"""Writes a iteration operation."""
		return self._format(
			"for %s in %s" % (
				self.write(iteration.getIteratedSlot()),
				self.write(iteration.getIterator())
			),
			self.write(iteration.getProcess()),
			"end"
		)

	def writeEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

# EOF
