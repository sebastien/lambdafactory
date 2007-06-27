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
# Last mod  : 27-Jun-2007
# -----------------------------------------------------------------------------

# TODO: When constructor is empty, should assign default attributes anyway

from modelwriter import AbstractWriter, flatten
from resolver import AbstractResolver
import interfaces, reporter
import os.path

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
		self.jsPrefix = ""
		self.jsCore   = "Extend."
		self.inInvocation = False

	def getRuntimeSource(s):
		"""Returns the JavaScript code for the runtime that is necassary to run
		the program."""
		this_file = os.path.abspath(__file__)
		js_runtime = os.path.join(os.path.dirname(this_file), "runtimes", "js", "extend+runtime.js")
		f = file(js_runtime, 'r') ; text = f.read() ; f.close()
		return text

	def getAbsoluteName( self, element ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [element.getName()]
		while element.getParent():
			element = element.getParent()
			# FIXME: Some elements may not have a name
			if not isinstance(element, interfaces.IProgram):
				names.insert(0, element.getName())
		return ".".join(names)

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "init"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name
	
	def writeModule( self, moduleElement):
		"""Writes a Module element."""
		code = [self._document(moduleElement),"var %s={}" % (moduleElement.getName())]
		for name, value in moduleElement.getSlots():
			if isinstance(value, interfaces.IModuleAttribute):
				code.extend(["%s.%s=%s" % (moduleElement.getName(), name, self.write(value.getDefaultValue()))])
			else: 
				code.extend(["%s.%s=%s" % (moduleElement.getName(), self.renameModuleSlot(name), self.write(value))])
		code.append("%s.init()" % (moduleElement.getName()))
		return self._format(
			*code
		)

	def writeImportOperation( self, importElement):
		return self._format("")

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		parent  = "undefined"
		if len(parents) == 1:
			parent = self.write(parents[0])
		elif len(parents) > 1:
			raise Exception("JavaScript back-end only supports single inheritance")
		# We create a map of class methods, including inherited class methods
		# so that we can copy the implementation of these
		classOperations = {}
		for name, meths in classElement.getInheritedClassMethods(self).items():
			# FIXME: Maybe use wrapper instead
			classOperations[name] = self._writeClassMethodProxy(classElement, meths[0])
		# Here, we've got to cheat a little bit. Each class method will 
		# generate an '_imp' suffixed method that will be invoked by the 
		for meth in classElement.getClassMethods():
			classOperations[meth.getName()] = meth
		classOperations = classOperations.values()
		classAttributes = {}
		for name, attributes in classElement.getInheritedClassAttributes(self).items():
			classAttributes[name] = self.write(attributes[0])
		for attribute in classElement.getClassAttributes():
			classAttributes[attribute.getName()] = self.write(attribute)
		classAttributes = classAttributes.values()
		result = []
		result.append(self._document(classElement))
		result.append("name:'%s', parent:%s," % (self.getAbsoluteName(classElement), parent))
		# We collect class attributes
		constructors = classElement.getConstructors()
		destructors  = classElement.getDestructors()
		methods      = classElement.getInstanceMethods()
		if constructors:
			assert len(constructors) == 1, "Multiple constructors are not supported yet"
			result.append("%s" % (self.write(constructors[0])))
		if destructors:
			assert len(destructors) == 1, "Multiple destructors are not supported"
			result.append("%s" % (self.write(destructors[0])))
		if methods:
			written_meths = ",\n".join(map(self.write, methods))
			result.append("methods:{")
			result.append([written_meths])
			result.append("},")
		if classAttributes:
			written_attrs = ",\n".join(map(self.write, classAttributes))
			result.append("attributes:{")
			result.append([written_attrs])
			result.append("},")
		if classOperations:
			written_ops = ",\n".join(map(self.write, classOperations))
			result.append("operations:{")
			result.append([written_ops])
			result.append("},")
		if result[-1][-1] == ",":result[-1] =result[-1][:-1]
		return self._format(
			"Extend.Class({",
			result,
			"})"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		return self._format(
			self._document(methodElement),
			"%s:function(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			["var __this__=this"],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		args        = methodElement.getArguments()
		return self._format(
			self._document(methodElement),
			"%s:function(%s){" % (method_name, ", ".join(map(self.write, args))),
			["var __this__ = this;"],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)
		
	def _writeClassMethodProxy(self, currentClass, inheritedMethodElement):
		"""This function is used to wrap class methods inherited from parent
		classes, so that inheriting operations from parent classes works
		properly. This may look a bit dirty, but it's the only way I found to
		implement this properly"""
		method_name = inheritedMethodElement.getName()
		method_args = inheritedMethodElement.getArguments()
		return self._format(
			"%s:function(%s){" % (method_name, ", ".join(map(self.write, method_args))),
			["return %s.%s.apply(%s, arguments);" % (
				self.getAbsoluteName(inheritedMethodElement.getParent()),
				method_name,
				self.getAbsoluteName(currentClass)
			)],
			'}'
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("__this__.%s = %s" % (a.getReferenceName(), self.write(a.getDefaultValue())))
		return self._format(
			self._document(element),
			"init:function(%s){" % (
				", ".join(map(self.write, element.getArguments()))
			),
			["var __this__=this"],
			self._writeClosureArguments(element),
			attributes or None,
			map(self.write, element.getOperations()),
			"}"
		)

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		return self._format(
			self._document(closure),
			"function(%s){" % ( ", ".join(map(self.write, closure.getArguments()))),
			self._writeClosureArguments(closure),
			map(self.write, closure.getOperations()),
			"}"
		)
	
	def writeClosureBody(self, closure):
		return self._format('{', map(self.write, closure.getOperations()), '}')

	def _writeClosureArguments(self, closure):
		i = 0
		l = len(closure.getArguments())
		result = []
		for argument in closure.getArguments():
			if argument.isRest():
				assert i >= l - 2
				result.append("%s = %s(arguments,%d)" % (
					argument.getReferenceName(),
					self.jsPrefix + self.jsCore + "sliceArguments",
					i
				))
			i += 1
		return result

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
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"function(%s){" % (
					", ".join(map(self.write, function.getArguments()))
				),
				[self._document(function)],
				['var __this__=%s;' % (self.getAbsoluteName(parent))],
				self._writeClosureArguments(function),
				self.writeFunctionWhen(function),
				map(self.write, function.getOperations()),
				"}"
			]
		else:
			res = [
				self._document(function),
				"function(%s){" % (
					", ".join(map(self.write, function.getArguments()))
				),
				self._writeClosureArguments(function),
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
			res = "%s:%s" % (element.getReferenceName(), self.write(default_value))
		else:
			res = "%s:undefined" % (element.getReferenceName())
		return self._format(self._document(element), res)

	def writeModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'undefined'
		return self._format(
			self._document(element),
			"%s=%s" % (element.getReferenceName(), default_value)
		)

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		value, scope = self.resolve(symbol_name)
		if scope and scope.hasSlot(symbol_name):
			value = scope.getSlot(symbol_name)
		if symbol_name == "self":
			return "__this__"
		if symbol_name == "target":
			return "this"
		elif symbol_name == "Undefined":
			return "undefined"
		elif symbol_name == "True":
			return "true"
		elif symbol_name == "False":
			return "false"
		elif symbol_name == "None":
			return "null"
		elif symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return "__this__.getSuper(%s)" % (
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
					return "__this__.getMethod('%s') " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				if self.isInInstanceMethod():
					return "__this__.getClass().%s" % (symbol_name)
				else:
					return "__this__.%s" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isInClassMethod():
					return "__this__.%s" % (symbol_name)
				else:
					return "__this__.getClass().%s" % (symbol_name)
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
				if not isinstance(scope, interfaces.IProgram):
					names.insert(0, scope.getName())
			return ".".join(names)
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassParents():
				return "__this__." + symbol_name
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
		elif isinstance(scope, interfaces.IProgram):
			return symbol_name
		elif isinstance(scope, interfaces.IBlock):
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
		if isinstance(start, interfaces.ILiteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILiteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = self.jsPrefix + self.jsCore + "range(%s,%s)" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self._write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		resolved_name = resolution.getReference().getReferenceName()
		if resolution.getContext():
			if resolved_name == "super":
				return "%s.getSuper()" % (self.write(resolution.getContext()))
			else:
				return "%s.%s" % (self.write(resolution.getContext()), resolved_name)
		else:
			return "%s" % (resolved_name)

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
			if operator.getReferenceName() == "has":
					res = '(typeof(%s.%s)!="undefined")' % (
					self.write(operands[0]),
					self.write(operands[1])
				)
			else:
				res = "%s %s %s" % (
					self.write(operands[0]),
					self.write(operator),
					self.write(operands[1])
				)
		if self._filterContext(interfaces.IComputation):
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

	def writeSelectionInExpression( self, selection ):
		rules  = selection.getRules()
		result = []
		text   = ""
		for rule in rules:
			#assert isinstance(rule, interfaces.IMatchExpressionOperation)
			if isinstance(rule, interfaces.IMatchExpressionOperation):
				expression = rule.getExpression()
			else:
				expression = rule.getProcess()
			text += "((%s) ? (%s) : " % (
				self.write(rule.getPredicate()),
				self.write(expression)
			)
		text += "undefined"
		for r in rules:
			text += ")"
		return text
	
	def writeSelection( self, selection ):
		# If we are in an assignataion and allocation which is contained in a
		# closure (because we can have a closure being assigned to something.)
		if self.isIn(interfaces.IAssignation) > self.isIn(interfaces.IClosure) \
		or self.isIn(interfaces.IAllocation) > self.isIn(interfaces.IClosure):
			return self.writeSelectionInExpression(selection)
		rules = selection.getRules()
		result = []
		for i in range(0,len(rules)):
			rule = rules[i]
			if isinstance(rule, interfaces.IMatchProcessOperation):	
				process = self.write(rule.getProcess()) 
			else:
				assert isinstance(rule, interfaces.IMatchExpressionOperation)
				process = "{%s}" % (self.write(rule.getExpression()))
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
			"%siterate(%s, %s, __this__)" % (
				self.jsPrefix + self.jsCore,
				self.write(iteration.getIterator()),
				self.write(iteration.getClosure())
			)
		)

	def writeRepetition( self, repetition ):
		return self._format(
			"while (%s)" % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess())
		)

	def writeAccessOperation( self, operation ):
		return self._format(
			"%s[%s]" % (self.write(operation.getTarget()), self.write(operation.getIndex()))
		)

	def writeSliceOperation( self, operation ):
		start = operation.getSliceStart()
		end   = operation.getSliceEnd()
		if start: start = self.write(start)
		else: start = "0"
		if end: end = self.write(end)
		else: end = "undefined"
		return self._format(
			"S.Core.slice(%s,%s,%s)" % (
				self.write(operation.getTarget()),
				start,
				end
		))

	def writeEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def writeBreaking( self, breking ):
		"""Writes a break operation."""
		return "break"
	
	def writeEmbed( self, embed ):
		lang = embed.getLanguage().lower().strip()
		assert lang in ("js", "javascript")
		return embed.getCodeString()
	
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
