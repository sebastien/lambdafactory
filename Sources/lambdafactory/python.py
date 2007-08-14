#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 03-Aug-2007
# Last mod  : 14-Aug-2007
# -----------------------------------------------------------------------------

# TODO: When constructor is empty, should assign default attributes anyway
# TODO: Support for variable and keyword arguments

from modelwriter import AbstractWriter, flatten
from resolver import AbstractResolver
import interfaces, reporter
import os.path

class Resolver(AbstractResolver):
	pass

#------------------------------------------------------------------------------
#
#  Python Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	def __init__( self, reporter=reporter.DefaultReporter ):
		AbstractWriter.__init__(self, reporter)
		self.resolver = Resolver(reporter=reporter)
		self.runtimePrefix = "__LambdaFactory__."
		self.supportedEmbedLanguages = ["python"]

	def getRuntimeSource(s):
		"""Returns the Python code for the runtime that is necassary to run
		the program."""
		return ""

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

	def getAbsoluteNameFromModule( self, element, module ):
		if element == module:
			return "__module__"
		parent = element.getParent()
		if parent:
			if parent == module:
				return element.getName()
			elif not isinstance(parent, interfaces.IProgram):
				return self.getAbsoluteNameFromModule(parent, module)+ "." + element.getName()
			else:
				return ""
		else:
			return element.getName()

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "init"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name
	
	def writeModule( self, moduleElement):
		"""Writes a Module element."""
		main = False
		code = [
			"# " + self.SNIP % ("%s.py" % (self.getAbsoluteName(moduleElement).replace(".", "/"))),
			self._document(moduleElement),
			"import sys",
			"__module__ = sys.modules[__name__]"
		]
		imports_offset = len(code)
		version = moduleElement.getAnnotation("version")
		code.append("__module_name__ = '%s'" % (self.getAbsoluteName(moduleElement)))
		if version:
			code.append("__version__ = '%s'" % (version.getContent()))
		module_init = []
		imports     = []
		for name, value in moduleElement.getSlots():
			# TODO: Sort values according to their dependencies
			if name == interfaces.Constants.ModuleInit:
				for o in value.getOperations():
					if isinstance(o, interfaces.IImportOperation):
						imports.append(self.write(o))
					else:
						module_init.append(self.write(o))
			else:
				code.append(self.write(value))
			if name == interfaces.Constants.MainFunction:
				main = value
		# We take care of the imports
		if imports:
			# NOTE: This is a bit dirty, but it helps preserve the import
			# order.
			imports.reverse()
			for i in imports:
				code.insert(imports_offset, i)
		# We take care of the module_init
		if module_init:
			code.extend(module_init)
		# We take care or the main function
		if main:
			code.extend([
				'if __name__ == "__main__":',
				[
					"import sys",
					"sys.exit(%s(sys.argv))" % (interfaces.Constants.MainFunction)
				]
			])
		return self._format(
			*code
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		if len(parents):
			# Remove object if we know one of the parent already extends object
			parents = "(%s,object):" % (", ".join(map(self.write, parents)))
		else:
			parents = "(object):"
		constructor  = None
		constructors = classElement.getConstructors()
		assert not constructors or len(constructors) == 1
		if constructors:
			constructor = [self.write(constructors[0])]
		elif not parents:
			constructor = [
				"def __init__(self):",
				[self._writeConstructorAttributes(classElement)]
			]
		c_attrs = classElement.getClassAttributes()
		c_inst  = classElement.getInstanceMethods()
		c_ops   = classElement.getClassMethods()
		if not c_attrs and not c_inst and not c_ops: empty = ["pass"]
		else: empty = None
		return self._format(
			self._document(classElement),
			"class %s%s" % (classElement.getName(), parents),
			flatten([self.write(m) for m in c_attrs]),
			constructor,
			flatten([self.write(m) for m in c_inst]),
			flatten([self.write(m) for m in c_ops]),
			empty,
			""
		)
	
	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		return self._format(
			self._document(methodElement),
			"def %s(%s):" % (
				method_name,
				self._writeMethodArguments(methodElement)
			),
			self._writeFunctionArgumentsInit(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()) or ["pass"],
			""
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		args        = methodElement.getArguments()
		return self._format(
			self._document(methodElement),
			"@classmethod",
			"def %s(%s):" % (method_name, self._writeMethodArguments(methodElement)),
			self._writeFunctionArgumentsInit(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()) or ["pass"],
			""
		)

	def _writeMethodArguments( self, method ):
		args = ", ".join(map(self.write, method.getArguments()))
		if args: return "self, " + args
		else: return "self"

	def _writeConstructorAttributes( self, element=None ):
		if element and isinstance(element, interfaces.IClass):
			current_class = element
		else:
			current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("self.%s = %s" % (a.getReferenceName(), self.write(a.getDefaultValue())))
		if not attributes: return None
		else: return self._format(attributes)

	def _writeFunctionArgumentsInit(self, function):
		"""Returns a list of operations that initialize the default attributes
		in case they weren't already."""
		result = []
		for argument in function.getArguments():
			if not (argument.getDefault() is None):
				a = argument.getReferenceName()
				result.append("if %s is None: %s = %s" % (
					a,
					a,
					self.write(argument.getDefault())
				))
		return result

	def writeConstructor( self, element ):
		"""Writes a method element."""
		arguments = self._writeMethodArguments(element)
		return self._format(
			self._document(element),
			"def __init__ (%s):" % (arguments),
			self._writeConstructorAttributes(element),
			self._writeFunctionArgumentsInit(element),
			map(self.write, element.getOperations()) or ["pass"],
			""
		)

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		# FIXME: Find a way to this properly
		return self._format(
			self._document(closure),
			"lambda %s:(" % ( ", ".join(map(self.write, closure.getArguments()))),
				", ".join(map(self.write, closure.getArguments())),
				self._writeFunctionArgumentsInit(closure),
				map(self.write, closure.getOperations()) or ["pass"],
			")"
		)

	def writeFunctionWhen(self, function ):
		res = []
		for a in function.annotations(withName="when"):
			res.append("if (not(%s)): return" % (self.write(a.getContent())))
		return self._format(res) or None

	def writeFunctionPost(self, function ):
		res = []
		for a in function.annotations(withName="post"):
			res.append("if (not (%s)): raise new Exception('Assertion failed')" % (self.write(a.getContent())))
		return self._format(res) or None
	
	def writeFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"def %s (%s):" % (
					name,
					", ".join(map(self.write, function.getArguments()))
				),
				[self._document(function)],
				['self=__module__'],
				self._writeFunctionArgumentsInit(function),
				self.writeFunctionWhen(function),
				map(self.write, function.getOperations()) or ["pass"],
				"\n"
			]
		else:
			res = [
				self._document(function),
				"def %s (%s)" % (
					name,
					", ".join(map(self.write, function.getArguments()))
				),
				self.writeFunctionWhen(function),
				map(self.write, function.getOperations()),
				"\n"
			]
		if function.annotations(withName="post"):
			res[0] = "__wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'self=__module__' )
			res.append("result = __wrapped__(__this__, **arguments)")
			res.append(self.writeFunctionPost(function))
			res.append("return result")
		return self._format(*res)

	def writeBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			*(map(self.write, block.getOperations()))
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		default = argElement.getDefault()
		if default is None:
			return "%s" % (argElement.getReferenceName())
		else:
			return "%s=None" % (argElement.getReferenceName())

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value="None"
		return self._format(
			self._document(element),
			"%s = %s" % (element.getReferenceName(), default_value)
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			res = "%s = %s" % (element.getReferenceName(), self.write(default_value))
		else:
			res = "%s = None" % (element.getReferenceName())
		return self._format(self._document(element), res)

	def writeModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'None'
		return self._format(
			self._document(element),
			"%s = %s" % (element.getReferenceName(), default_value)
		)

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		value, scope = self.resolve(symbol_name)
		if scope and scope.hasSlot(symbol_name):
			value = scope.getSlot(symbol_name)
		if symbol_name == "self":
			return "self"
		if symbol_name == "target":
			return "self"
		elif symbol_name == "Undefined":
			return "None"
		elif symbol_name == "True":
			return "True"
		elif symbol_name == "False":
			return "False"
		elif symbol_name == "None":
			return "None"
		elif symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return "super(self,%s)" % (
				self.getAbsoluteNameFromModule(self.getCurrentClass(), self.getCurrentModule())
			)
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return "print "
			else: return symbol_name
		# It is a method of the current class
		elif self.getCurrentClass() == scope:
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "self.%s" % (symbol_name)
				else:
					return "self.%s " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				if self.isInInstanceMethod():
					return "self.__class__.%s" % (symbol_name)
				else:
					return "self.%s" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isInClassMethod():
					return "self.%s" % (symbol_name)
				else:
					return "self.__class__.%s" % (symbol_name)
			else:
				return "self." + symbol_name
		# It is a local variable
		elif self.getCurrentFunction() == scope:
			return symbol_name
		# It is a property of a module
		elif isinstance(scope, interfaces.IModule):
			if scope == self.getCurrentModule():
				return symbol_name
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
				return "self." + symbol_name
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

	OPERATORS = {
				"and":"and",
				"is":"==",
				"is not":"!=",
				"not":"not",
				"or":"or"
	}
	def writeOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = self.OPERATORS.get(o) or o
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
			return "%s=%s" % (s.getReferenceName(), self.write(v))
		else:
			return "%s" % (s.getReferenceName())

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
		if isinstance(start, interfaces.ILiteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILiteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		step = operation.getStep()
		if step:
			res = "range(%s,%s,%s)" % (start, end, self.write(step))
		else:
			res = "range(%s,%s)" % (start, end)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		resolved_name = resolution.getReference().getReferenceName()
		if resolution.getContext():
			if resolved_name == "super":
				return "super(%s,self)" % (self.write(resolution.getContext()))
			elif resolution.getContext() == self.getCurrentModule():
				return "%s" % (resolve_name)
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
					res = '(hasattr(%s,"%s"))' % (
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
		return "%s(%s)" % (
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
			text += "(%s) and (%s) or " % (
				self.write(rule.getPredicate()),
				self.write(expression)
			)
		text += "None"
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
				process = "%s" % (self.write(rule.getExpression()))
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
				process = 'pass'
			if i==0:
				rule_code = (
					"if %s:" % (self.write(rule.getPredicate())),
					process,
				)
			else:
				rule_code = (
					"elif %s:" % (self.write(rule.getPredicate())),
					process,
				)
			result.extend(rule_code)
		return self._format(*result)

	def writeIteration( self, iteration ):
		"""Writes a iteration operation."""
		it_name = self._unique("_iterator")
		iterator = iteration.getIterator()
		closure  = iteration.getClosure()
		args  = map(lambda a:a.getName(), closure.getArguments())
		if len(args) == 0: args.append("__iterator_value")
		if len(args) == 1: args.append("__iterator_index")
		i = args[1]
		v = args[0]
		return self._format(
				"for %s in %s:" % (v, self.write(iterator)),
				map(self.write, closure.getOperations())
		)
		

	def writeRepetition( self, repetition ):
		return self._format(
			"while %s:" % (self.write(repetition.getCondition())),
			[self.write(repetition.getProcess())]
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
		else: end = ""
		return self._format(
			"%s[%s:%s]" % (
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
	
	def writeExcept( self, exception ):
		"""Writes a except operation."""
		return "raise " + self.write(exception.getValue())
	
	def writeInterception( self, interception ):
		"""Writes an interception operation."""
		try_block   = interception.getProcess()
		try_catch   = interception.getIntercept()
		try_finally = interception.getConclusion()
		res         = ["try:", map(self.write, try_block.getOperations())]
		if try_catch:
			res.extend([
				"except Exception, %s:" % ( self.write(try_catch.getArguments()[0])) ,
				map(self.write, try_catch.getOperations())
			])
		if try_finally:
			res.extend(["finally:", map(self.write, try_finally.getOperations())])
		return self._format(*res)

	def writeImportOperation( self, importElement):
		imported_name = self.write(importElement.getImportedElement())
		imported_elem = imported_name.split(".")[-1]
		if importElement.getAlias():
			return "import %s as %s" % (importElement.getAlias().getReferenceName(), imported_name)
		else:
			if imported_name[-1] == "*":
				return "from %s import *" % (imported_name[:-2])
			return "import %s" % (imported_name)
		
	def writeEmbed( self, embed ):
		lang = embed.getLanguage().lower().strip()
		assert lang in self.supportedEmbedLanguages
		return embed.getCodeString()
	
	def _document( self, element ):
		if element.hasDocumentation():
			doc = element.getDocumentation()
			res = []
			for line in doc.getContent().split("\n"):
				res.append("# " + line)
			return "\n".join(res)
		else:
			return None

# EOF