#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 09-Jan-2007
# Last mod  : 09-jan-2007
# -----------------------------------------------------------------------------

from modelwriter import AbstractWriter, flatten
from resolver import AbstractResolver
import interfaces, reporter

class Resolver(AbstractResolver):
	pass

#------------------------------------------------------------------------------
#
#  C Writer
#
#------------------------------------------------------------------------------

class CLib:
	
	def __init__(self, prefix="sugar"):
		self.p = prefix
		
	def resolve(self, name, context=None):
		if context:
			return "%s_resolve(%s)" % (self.p, name)
		else:
			return "%s_resolve(%s, context)" % (self.p, context)
			
class Writer(AbstractWriter):

	def __init__( self, reporter=reporter.DefaultReporter ):
		AbstractWriter.__init__(self, reporter)
		self.resolver = Resolver(reporter=reporter)
		self.c     = CLib()
		self.jsPrefix = "XXX"
		self.jsCore = "XXX"
		
	def getAbsoluteName( self, element ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [element.getName()]
		while element.getParent():
			element = element.getParent()
			names.insert(0, element.getName())
		res = self.c.resolve(names[0])	
		for name in names[1:]:
			res = self.c.resolve(name, res)	
		return res

	def writeModule( self, moduleElement ):
		"""Writes a Module element."""
		return self._format("var %s = {" % (moduleElement.getName()),
			[self.write(s[1]) + "," for s in moduleElement.getSlots()],
			"MODULE:{name:'%s'}" % (moduleElement.getName()),
			"}"
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		parent  = "undefined"
		if len(parents) == 1:
			parent = self.write(parents[0])
		elif len(parents) > 1:
			raise Exception("JavaScript back-end only supports single inheritance")
		return self._format(
			self._document(classElement),
			"%s: Class.create({" % (classElement.getName()),
			flatten([self.write(m) +"," for m in classElement.getAttributes()]),
			flatten([self.write(m) +"," for m in classElement.getClassAttributes()]),
			flatten([self.write(m) +"," for m in classElement.getMethods()]),
			# FIXME
			flatten([self.write(m) +"," for m in classElement.getClassMethods()]),
			"\n\tCLASSDEF:{name:'%s', parent:%s}" % (classElement.getName(), parent),
			"})"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "initialize"
		if method_name == interfaces.Constants.Destructor:  method_name = "destroy"
		return self._format(
			self._document(methodElement),
			"%s:function(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.ModuleInit:  method_name = "initializeModule"
		return self._format(
			self._document(methodElement),
			"%s:function(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		return self._format(
			self._document(element),
			"initialize:function(%s){" % (
				", ".join(map(self.write, element.getArguments()))
			),
			map(self.write, element.getOperations()),
			"}"
		)

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		return self._format(
			self._document(closure),
			"function(%s){" % ( ", ".join(map(self.write, closure.getArguments()))),
			map(self.write, closure.getOperations()),
			"}"
		)

	def writeFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()
		if name == interfaces.Constants.ModuleInit: name = "initializeModule"
		if name == interfaces.Constants.MainFunction: name = "main"
		if parent and isinstance(parent, interfaces.IModule):
			return self._format(
				self._document(function),
				"%s:function(%s){" % (
					name,
					", ".join(map(self.write, function.getArguments()))
				),
				map(self.write, function.getOperations()),
				"}"
			)
		else:
			return self._format(
				self._document(function),
				"function%s(%s){" % (
					name,
					", ".join(map(self.write, function.getArguments()))
				),
				map(self.write, function.getOperations()),
				"}"
			)

	def writeBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			"{",
			map(self.write, block.getOperations()),
			"}"
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s" % (
			argElement.getReferenceName(),
		)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		return "%s: undefined" % (
			element.getReferenceName(),
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		return "%s: undefined" % (
			element.getReferenceName(),
		)

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		target      = self.resolve(symbol_name)
		if symbol_name == "self":
			return "this"
		elif symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return self.jsPrefix + self.jsCore + "superFor(%s, this)" % (
				self.getAbsoluteName(self.getCurrentClass())
			)
		if not target:
			return symbol_name
		elif self.getCurrentClass() == target:
			return "this." + symbol_name
		elif self.getCurrentFunction() == target:
			return symbol_name
		elif isinstance(target, interfaces.IModule):
			names = [target.getName(), symbol_name]
			while target.getParent():
				target = target.getParent()
				names.insert(0, target.getName())
			return ".".join(names)
		# Target is a class
		elif isinstance(target, interfaces.IClass):
			# And the class is one of the parent class
			if target in self.getCurrentClassParents():
				return "this." + symbol_name
			# Otherwise it is an outside class, and we have to check that the
			# value is not an instance slot
			else:
				names = [target.getName(), symbol_name]
				while target.getParent():
					target = target.getParent()
					names.insert(0, target.getName())
				return ".".join(names)
		# FIXME: This is an exception... iteration being an operation, not a
		# context...
		elif isinstance(target, interfaces.IIteration):
			return symbol_name
		else:
			raise Exception("Unsupported scope:" + str(target))

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
		if v:
			return "var %s = %s" % (s.getReferenceName(), self.write(v))
		else:
			return "var %s" % (s.getReferenceName())

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			self.write(assignation.getTarget()),
			self.write(assignation.getAssignedValue())
		)

	def writeEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart() 
		end   = operation.getEnd() 
		if isinstance(start, interfaces.ILitteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILitteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = self.jsPrefix + self.jsCore + "range(%s,%s)" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self._write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		if resolution.getContext():
			return "%s.%s" % (self.write(resolution.getContext()), resolution.getReference().getReferenceName())
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

	def writeInstanciation( self, operation ):
		"""Writes an invocation operation."""
		return "new %s(%s)" % (
			self.write(operation.getInstanciable()),
			", ".join(map(self.write, operation.getArguments()))
		)

	def writeSelection( self, selection ):
		rules = selection.getRules()
		result = []
		for i in range(0,len(rules)):
			rule = rules[i]
			if i==0:
				rule_code = (
					"if ( %s )" % (self.write(rule.getPredicate())),
					self.write(rule.getProcess()),
				)
			else:
				rule_code = (
					"else if ( %s )" % (self.write(rule.getPredicate())),
					self.write(rule.getProcess()),
				)
			result.extend(rule_code)
		return self._format(*result)

	def writeIteration( self, iteration ):
		"""Writes a iteration operation."""
		it_name = self._unique("_iterator")
		return self._format(
			"var %s = %s" % (
				it_name,
				self.write(iteration.getIterator())
			),
			"while ( %s.hasNext() ) {" % ( it_name),
			(
				"var %s = %s.next()" % (
					self.write(iteration.getIteratedSlot()),
					it_name
				),
				self.write(iteration.getProcess())
			),
			"}"
		)

	def writeSliceOperation( self, operation ):
		return self._format(
			"%s[%s]" % (self.write(operation.getTarget()), self.write(operation.getSlice()))
		)

	def writeEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def _document( self, element ):
		if element.hasDocumentation():
			return "# " + element.getDocumentation()
		else:
			return None

# EOF