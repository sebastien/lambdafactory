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
# Last mod  : 04-jan-2007
# -----------------------------------------------------------------------------


from modelwriter import AbstractWriter, flatten, notEmpty
from resolver import AbstractResolver
import interfaces, reporter

class Resolver(AbstractResolver):
	pass

#------------------------------------------------------------------------------
#
#  JavaScript Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	def __init__( self, reporter=reporter.DefaultReporter ):
		AbstractWriter.__init__(self, reporter)
		self.resolver = Resolver(reporter=reporter)
		self.jsPrefix = "S."
		self.jsCore   = "Core."
		self.inInvocation = False

	def getAbsoluteName( self, element ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [element.getName()]
		while element.getParent():
			element = element.getParent()
			names.insert(0, element.getName())
		return ".".join(names)

	def writeModule( self, moduleElement, contentOnly=False ):
		"""Writes a Module element."""
		return self._format("var %s = {" % (moduleElement.getName()),
			[self.write(s[1]) + "," for s in moduleElement.getSlots()],
			"MODULE:{name:'%s'}" % (moduleElement.getName()),
			"}",
			"%s.initialize()" % (moduleElement.getName())
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
			notEmpty(flatten([self.write(m) +"," for m in classElement.getAttributes()])),
			notEmpty(flatten([self.write(m) +"," for m in classElement.getConstructors()])),
			notEmpty(flatten([self.write(m) +"," for m in classElement.getDestructors()])),		
			notEmpty(flatten([self.write(m) +"," for m in classElement.getInstanceMethods()])),
			"\n\tCLASSDEF:{name:'%s', parent:%s}" % (classElement.getName(), parent),
			"}, {",
			notEmpty([", ".join(flatten([self.write(m) for m in classElement.getClassAttributes()]))]),
			notEmpty([", ".join(flatten([self.write(m) for m in classElement.getClassMethods()]))]),
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
			["var __this__ = this"],
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		return self._format(
			self._document(methodElement),
			"%s:function(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("this.%s = %s" % (a.getReferenceName(), self.write(a.getDefaultValue())))
		return self._format(
			self._document(element),
			"initialize:function(%s){" % (
				", ".join(map(self.write, element.getArguments()))
			),
			["var __this__ = this"],
			attributes or None,
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
	
	def writeClosureBody(self, closure):
		return self._format('{', map(self.write, closure.getOperations()), '}')

	def writeFunctionWhen(self, function ):
		res = []
		for a in function.annotations(withName="when"):
			res.append("if (!(%s)) { return }" % (self.write(a.getContent())))
		return self._format(res) or None

	def writeFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()
		if name == interfaces.Constants.ModuleInit: name = "initialize"
		if name == interfaces.Constants.MainFunction: name = "main"
		if parent and isinstance(parent, interfaces.IModule):
			return self._format(
				self._document(function),
				"%s:function(%s){" % (
					name,
					", ".join(map(self.write, function.getArguments()))
				),
				self.writeFunctionWhen(function),
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
				self.writeFunctionWhen(function),
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
		default_value = element.getDefaultValue()
		if default_value:
			return "%s: %s" % (element.getReferenceName(), self.write(default_value))
		else:
			return "%s: undefined" % (element.getReferenceName())

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		target      = self.resolve(symbol_name)
		value       = None
		if target and target.hasSlot(symbol_name):
			value = target.getSlot(symbol_name)
		if symbol_name == "self":
			return "this"
		elif symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return self.jsPrefix + self.jsCore + "superFor(%s, this)" % (
				self.getAbsoluteName(self.getCurrentClass())
			)
		# If there is no target, then the symmbol is undefined
		if not target:
			if symbol_name == "print": return "console.log"
			else: return symbol_name
		# It is a method of the current class
		elif self.getCurrentClass() == target:
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "this.%s" % (symbol_name)
				else:
					return self.jsPrefix + self.jsCore + "wrapMethod(__this__,'%s') " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				return "%s.%s" % (self.getAbsoluteName(self.getCurrentClass()), symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				return "%s.%s" % (self.getAbsoluteName(self.getCurrentClass()), symbol_name)
			else:
				return "this." + symbol_name
		# It is a local variable
		elif self.getCurrentFunction() == target:
			return symbol_name
		# It is a property of a module
		elif isinstance(target, interfaces.IModule):
			names = [target.getName(), symbol_name]
			while target.getParent():
				target = target.getParent()
				names.insert(0, target.getName())
			return ".".join(names)
		# It is a property of a class
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

	JS_OPERATORS = {
				"and":"&&",
				"is":"==",
				"is not":"!=",
				"not":"!",
				"or":"||"
	}
	def writeOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = self.JS_OPERATORS.get(o) or o
		return "%s" % (o)

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

	def writeDictKey( self, key ):
		if isinstance(key, interfaces.IString):
			return self.write(key)
		else:
			# FIXME: Raise an error, because JavaScript only allow strings as keys
			return "(%s)" % (self.write(key))
		
	def writeDict( self, element ):
		return '{%s}' % (", ".join([
			"%s:%s" % ( self.writeDictKey(k),self.write(v))
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
		operands = filter(lambda x:x!=None,computation.getOperands())
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
		self.inInvocation = True
		t = self.write(invocation.getTarget())
		self.inInvocation = False
		return "%s(%s)" % (
			t,
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
			process = rule.getProcess() 
			# If the rule process is a block/closure, we simply expand the
			# closure. So we have
			# if (...) { code }
			# instead of
			# if (...) { (function(){code})() }
			if process and isinstance(process, interfaces.IClosure):
				process = self.writeClosureBody(process)
			elif process:
				process = "{(%s)()}" % (self.write(process))
			else:
				process = '{}'
			if i==0:
				rule_code = (
					"if ( %s )" % (self.write(rule.getPredicate())),
					process,
				)
			else:
				rule_code = (
					"else if ( %s )" % (self.write(rule.getPredicate())),
					process,
				)
			result.extend(rule_code)
		return self._format(*result)

	def writeIteration( self, iteration ):
		"""Writes a iteration operation."""
		it_name = self._unique("_iterator")
		return self._format(
			"%siterate(%s, %s, __this__)" % (
				self.jsPrefix + self.jsCore,
				self.write(iteration.getIterator()),
				self.write(iteration.getClosure())
			)
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
			doc = element.getDocumentation()
			res = []
			for line in doc.getContent().split("\n"):
				res.append("// " + line)
			return "\n".join(res)
		else:
			return None

# EOF