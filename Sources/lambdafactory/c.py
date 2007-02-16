#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 16-Feb-2007
# Last mod  : 16-Feb-2007
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


class RuntimeWriter:

	def __init__(self, writer):
		self.writer = writer
		self.write  = self.writer.write
	
	def op(self, name):
		return "Sugar_Core_" + name
	
	def new(self, classElement):
		return self.op("new(%s)" % (self.writer.getAbsoluteName(classElement))) 
	
	def newClass(self, classElement):
		parents = classElement.getSuperClasses()
		parent  = parents and self.write(parents[0]) or "UNDEFINED"
		return self.op("newClass(%s, %s)" % (
			self.writer.getAbsoluteName(classElement),
			parent
		))

	def range(self):
		pass
	
	def superFor(self):
		pass

	def iterate(self, iterator, closure):
		return self.op("iterate(%s,{%s;})" %(
			self.write(iterator),
			self.write(closure)
		))

	def typeFor(self, element):
		if isinstance(element, interfaces.IModule):
			return "PModule*"
		elif isinstance(element, interfaces.IClass):
			return "PClass*"
		else:
			return "PValue*"

	def slice(self, target, slice):
		return self.op("slice(%s,%s)" % (
			self.write(operation.getTarget()),
			self.write(operation.getSlice())
		))

class Writer(AbstractWriter):

	def __init__( self, reporter=reporter.DefaultReporter ):
		AbstractWriter.__init__(self, reporter)
		self.resolver = Resolver(reporter=reporter)
		self.jsPrefix = "S."
		self.jsCore   = "Core."
		self.inInvocation = False
		self.runtime = RuntimeWriter(self)
		self.closureCounter = 0
		
	def generateClosureName(self, closure):
		parent = closure.getParent()
		res = "%s_lambda%s" % (
			parent and self.getAbsoluteName(parent) or "GLOBAL",
			self.closureCounter
		)
		self.closureCounter += 1
		return res

	def getAbsoluteName( self, element, rename=None ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [rename or element.getName()]
		while element.getParent():
			element = element.getParent()
			names.insert(0, element.getName())
		return "_".join(names)

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "initialize"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name
	
	def writeModule( self, moduleElement, contentOnly=False ):
		"""Writes a Module element."""
		code = [
			"// TODO: Add reflexion support",
			self._document(moduleElement),"SModule* %s;\n" % (moduleElement.getName())
		]
		code.extend(["%s" % (self.write(s[1])) for s in moduleElement.getSlots()])
		code = [
			"DECLARE_MODULE(%s)\n" % (self.getAbsoluteName(moduleElement)),
			code,
			"\nEND_MODULE"
		]
		return self._format(
			*code
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		parent  = "UNDEFINED"
		class_name = self.getAbsoluteName(classElement)
		if len(parents) == 1:
			parent = self.write(parents[0])
		elif len(parents) > 1:
			raise Exception("JavaScript back-end only supports single inheritance")
		return self._format(
			"DECLARE_CLASS(%s)" % (class_name),
				[	self._document(classElement),
					"\n".join(map(self.write, flatten(
					"SClass* %s=%s;\n" % (class_name, self.runtime.newClass(classElement)),
					classElement.getAttributes(),
					classElement.getConstructors(),
					classElement.getDestructors(),		
					classElement.getInstanceMethods()
				)))],
			
				["\n".join(map(self.write, flatten(
					classElement.getClassAttributes(),
					classElement.getClassMethods()
				)))],
			"END_CLASS\n"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "initialize"
		if method_name == interfaces.Constants.Destructor:  method_name = "destroy"
		full_name = self.getAbsoluteName(methodElement, method_name)
		return self._format(
			self._document(methodElement),
			"SValue* %s(SObject* this, %s){" % (
				full_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			self.writeFunctionWhen(methodElement),
			map(self.writeCStatement, methodElement.getOperations()),
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = self.getAbsoluteName(methodElement)
		return self._format(
			self._document(methodElement),
			"SValue* %s(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			["SClass* this=%s;" % (self.getAbsoluteName(methodElement.getParent()))],
			self.writeFunctionWhen(methodElement),
			map(self.writeCStatement, methodElement.getOperations()),
			"}"
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		current_class = self.getCurrentClass()
		type_name     = self.getAbsoluteName(current_class)
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("this.%s = %s" % (a.getReferenceName(), self.write(a.getDefaultValue())))
		return self._format(
			self._document(element),
			"%s* initialize(%s){" % (
				type_name,
				", ".join(map(self.write, element.getArguments()))
			),
			["%s* this=%s;" % (type_name, self.runtime.new(current_class))],
			attributes or None,
			map(self.writeCStatement, element.getOperations()),
			["return this;"],
			"}"
		)

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		name = self.generateClosureName(closure)
		return self._format(
			self._document(closure),
			"PValue* %s(%s){" % ( 
				name,
				", ".join(map(self.write, closure.getArguments()))
			),
			map(self.writeCStatement, closure.getOperations()),
			"}; %s" % (name)
		)
	
	def writeClosureBody(self, closure):
		return self._format('{', map(writeCStatement, closure.getOperations()), '}')

	def writeFunctionWhen(self, function ):
		res = []
		for a in function.annotations(withName="when"):
			res.append("if (!(%s)) {return}" % (self.write(a.getContent())))
		return self._format(res) or None

	def writeFunctionPost(self, function ):
		res = []
		for a in function.annotations(withName="post"):
			res.append("if (!(%s)) {throw new Exception('Assertion failed')}" % (self.write(a.getContent())))
		return self._format(res) or None
	
	def writeFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()
		full_name = self.getAbsoluteName(function)
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"PValue* %s (%s){" % (
					full_name,
					", ".join(map(self.write, function.getArguments()))
				),
				[self._document(function)],
				['%s this=%s' % (self.runtime.typeFor(parent), self.getAbsoluteName(parent))],
				self.writeFunctionWhen(function),
				map(self.write, function.getOperations()),
				"}"
			]
		else:
			res = [
				self._document(function),
				"function %s){" % (
					", ".join(map(self.write, function.getArguments()))
				),
				self.writeFunctionWhen(function),
				map(self.write, function.getOperations()),
				"}"
			]
		if function.annotations(withName="post"):
			res[0] = "var __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'var __this__=%s;' % (self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(__this__, arguments);")
			res.append(self.writeFunctionPost(function))
			res.append("return result;")
		return self._format(res)

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
		return self._format(
			self._document(element),
			"%s:undefined" % (element.getReferenceName())
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			return "%s:%s" % (element.getReferenceName(), self.write(default_value))
		else:
			return "%s:undefined" % (element.getReferenceName())

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		scope      = self.resolve(symbol_name)
		value       = None
		if scope and scope.hasSlot(symbol_name):
			value = scope.getSlot(symbol_name)
		if symbol_name == "self":
			return "this"
		elif symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return self.jsPrefix + self.jsCore + "superFor(%s, this)" % (
				self.getAbsoluteName(self.getCurrentClass())
			)
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return self.jsPrefix + self.jsCore + "print"
			else: return symbol_name
		# It is a method of the current class
		elif self.getCurrentClass() == scope:
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "__this__.%s" % (symbol_name)
				else:
					return self.jsPrefix + self.jsCore + "wrapMethod(__this__,'%s') " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				return "%s.%s" % (self.getAbsoluteName(self.getCurrentClass()), symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				return "%s.%s" % (self.getAbsoluteName(self.getCurrentClass()), symbol_name)
			else:
				return "__this__." + symbol_name
		# It is a local variable
		elif self.getCurrentFunction() == scope:
			return symbol_name
		# It is a property of a module
		elif isinstance(scope, interfaces.IModule):
			names = [scope.getName(), symbol_name]
			while scope.getParent():
				scope = scope.getParent()
				names.insert(0, scope.getName())
			return ".".join(names)
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassParents():
				return "this." + symbol_name
			# Otherwise it is an outside class, and we have to check that the
			# value is not an instance slot
			else:
				names = [scope.getName(), symbol_name]
				while scope.getParent():
					scope = scope.getParent()
					names.insert(0, scope.getName())
				return ".".join(names)
		# FIXME: This is an exception... iteration being an operation, not a
		# context...
		elif isinstance(scope, interfaces.IIteration):
			return symbol_name
		elif isinstance(scope, interfaces.IClosure):
			return symbol_name
		else:
			raise Exception("Unsupported scope:" + str(scope))

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
			return "var %s=%s;" % (s.getReferenceName(), self.write(v))
		else:
			return "var %s;" % (s.getReferenceName())

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s;" % (
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
		# FIXME: Add rules to remove unnecessary parens
		if len(operands) == 1:
			res = "%s %s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			res = "%s %s %s" % (
				self.write(operands[0]),
				self.write(operator),
				self.write(operands[1])
			)
		if filter(lambda x:isinstance(x, interfaces.IComputation), self.contexts[:-1]):
			res = "(%s)" % (res)
		return res

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
				process = "%s" % (self.write(process))
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
			self.runtime.iterate(
				iteration.getIterator(),
				iteration.getClosure()
			)
		)

	def writeSliceOperation( self, operation ):
		return self._format(
			self.runtime.slice(operation.getTarget(), operation.getSlice()) 
		)

	def writeEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def writeCStatement(self, *args):
		return self.write(*args) + ";"
	
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