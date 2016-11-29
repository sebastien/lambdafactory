# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 03-Aug-2007
# Last mod  : 22-Jan-2013
# -----------------------------------------------------------------------------

# TODO: When constructor is empty, should assign default attributes anyway
# TODO: Support for variable and keyword arguments

from lambdafactory.modelwriter import AbstractWriter, flatten
import lambdafactory.interfaces as interfaces
import lambdafactory.reporter as reporter
from lambdafactory.splitter import SNIP
import os.path, re, time, string, random

#------------------------------------------------------------------------------
#
#  Python Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	def __init__( self ):
		AbstractWriter.__init__(self)
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

	def onModule( self, moduleElement):
		"""Writes a Module element."""
		main = False
		code = [
			"#" + SNIP % ("%s.py" % (self.getAbsoluteName(moduleElement).replace(".", "/"))),
			"#!/usr/bin/env python",
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
		imports.extend(moduleElement.getImportOperations())
		for name, value in moduleElement.getSlots():
			# TODO: Sort values according to their dependencies
			if name == interfaces.Constants.ModuleInit:
				module_init = value.getOperations()
			else:
				value_code = self.write(value)
				code.append(value_code)
			if name == interfaces.Constants.MainFunction:
				main = value
		# We take care of the imports
		if imports:
			# NOTE: This is a bit dirty, but it helps preserve the import
			# order.
			imports.reverse()
			for i in imports:
				code.insert(imports_offset, self.write(i))
		# We take care of the module_init
		if module_init:
			init_code = ["def __module_init__():", list(map(self.write,module_init))]
			init_code.append("__module_init__()")
			code.extend(init_code)
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

	def onClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getParentClassesRefs()
		if len(parents):
			# Remove object if we know one of the parent already extends object
			# FIXME: This does not seem to work with complex inheritance
			# parents = "(%s,object):" % (", ".join(map(self.write, parents)))
			parents = "(%s):" % (", ".join(map(self.write, parents)))
		else:
			# FIXME: This does not seem to work with complex inheritance
			#parents = "(object):"
			parents = ":"
		constructor  = None
		constructors = classElement.getConstructors()
		attributes   = classElement.getAttributes()
		assert not constructors or len(constructors) == 1
		if constructors:
			# Write provided constructor
			constructor = [self.write(constructors[0])]
		else:
			# We write the default constructor, see 'onConstructor' for for
			# FIXME: This is borrowed from the JS backend
			constructor               = []
			constructor_body          = []
			invoke_parent_constructor = None
			# FIXME: Implement proper attribute initialization even in
			# subclasses
			# We have to do the following JavaScript code because we're not
			# sure to know the parent constructors arity -- this is just a
			# way to cover our ass. We encapsulate the __super__ declaration
			# in a block to avoid scoping problems.
			is_first = True
			for parent in classElement.getParentClassesRefs():
				if is_first:
					constructor_body.insert(0,"%s.__init__(self, *args, **kwargs)" % (self.write(parent)))
				else:
					constructor_body.insert(0,"%s.__init__(self)" % (self.write(parent)))
				is_first = False
			# FIXME: This could probably be removed
			#for a in classElement.getAttributes():
			#	if not a.getDefaultValue(): continue
			#	constructor_body.append(
			#		"self.%s = %s};" % (
			#			self.jsSelf, self._rewriteSymbol(a.getName()),
			#			self.write(a.getDefaultValue())
			#	))
			# NOTE: We only need a default constructor when we have class attributes
			# declared and no constructor declared
			constructor_attributes = self._writeConstructorAttributes(classElement)
			if constructor_attributes:
				constructor = [
					"def __init__( self, *args, **kwargs ):",
					['"""Constructor wrapper to intialize class attributes"""'],
					constructor_body,
					constructor_attributes,
				]
		c_attrs = classElement.getClassAttributes()
		c_inst  = classElement.getInstanceMethods()
		c_ops   = classElement.getClassMethods()
		if not c_attrs and not c_inst and not c_ops: empty = ["pass"]
		else: empty = None
		return self._format(
			"class %s%s" % (classElement.getName(), parents),
			[self._document(classElement)],
			flatten([self.write(m) for m in c_attrs]),
			constructor,
			flatten([self.write(m) for m in c_inst]),
			flatten([self.write(m) for m in c_ops]),
			empty,
			""
		)

	def onMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		# TODO: If abstract, raise exception
		default_body = ["pass"]
		if methodElement.isAbstract():
			default_body = [
				'raise Exception("Abstract method %s.%s not implemented in: " + str(self))' % (
					self.getCurrentClass().getName(),
					method_name
				)
			]
		return self._format(
			"def %s(%s):" % (
				method_name,
				self._writeMethodArguments(methodElement)
			),
			[self._document(methodElement)],
			self._writeFunctionArgumentsInit(methodElement),
			#self.writeFunctionWhen(methodElement),
			list(map(self.write, methodElement.getOperations())) or default_body,
			""
		)

	def onClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		args        = methodElement.getParameters()
		default_body = ["pass"]
		if methodElement.isAbstract():
			default_body = [
				'raise Exception("Abstract method %s.%s not implemented")' % (
					self.getCurrentClass().getName(),
					method_name
				)
			]
		return self._format(
			"@classmethod",
			"def %s(%s):" % (method_name, self._writeMethodArguments(methodElement)),
			[self._document(methodElement)],
			self._writeFunctionArgumentsInit(methodElement),
			#self.writeFunctionWhen(methodElement),
			list(map(self.write, methodElement.getOperations())) or default_body,
			""
		)

	def _writeMethodArguments( self, method ):
		args = ", ".join(map(self.write, method.getParameters()))
		if args: return "self, " + args
		else: return "self"

	def _writeConstructorAttributes( self, element=None ):
		if element and isinstance(element, interfaces.IClass):
			current_class = element
		else:
			current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			default_value = a.getDefaultValue()
			if not default_value: default_value = "None"
			else: default_value = self.write(default_value)
			attributes.append("self.%s = %s" % (a.getName(), default_value))
		if not attributes: return None
		else: return self._format(attributes)

	def _writeFunctionArgumentsInit(self, function):
		"""Returns a list of operations that initialize the default attributes
		in case they weren't already."""
		result = []
		for argument in function.getParameters():
			if not (argument.getDefaultValue() is None):
				a = argument.getName()
				result.append("if %s is None: %s = %s" % (
					a,
					a,
					self.write(argument.getDefaultValue())
				))
		return result

	def onConstructor( self, element ):
		"""Writes a method element."""
		arguments = self._writeMethodArguments(element)
		return self._format(
			self._document(element),
			"def __init__ (%s):" % (arguments),
			self._writeConstructorAttributes(element),
			self._writeFunctionArgumentsInit(element),
			list(map(self.write, element.getOperations())) or ["pass"],
			""
		)

	def onClosure( self, closure ):
		"""Writes a closure element."""
		# FIXME: Find a way to this properly
		return self._format(
			self._document(closure),
			"lambda %s:(" % ( ", ".join(map(self.write, closure.getParameters()))),
				", ".join(map(self.write, closure.getParameters())),
				self._writeFunctionArgumentsInit(closure),
				list(map(self.write, closure.getOperations())) or ["pass"],
			")"
		)

	def doPrepareClosure( self, closure, name ):
		"""Writes a closure element as a defined function."""
		# FIXME: Find a way to this properly
		return self._format(
			self._document(closure),
			"def %s(%s):" % (name, ", ".join(map(self.write, closure.getParameters()))),
				self._writeFunctionArgumentsInit(closure),
				list(map(self.write, closure.getOperations())) or ["pass"],
			")"
		)

	def onFunctionWhen(self, function ):
		res = []
		for a in function.getAnnotations("when"):
			res.append("if (not(%s)): return" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunctionPost(self, function ):
		res = []
		for a in function.getAnnotations("post"):
			res.append("if (not (%s)): raise new Exception('Assertion failed')" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"def %s (%s):" % (
					name,
					", ".join(map(self.write, function.getParameters()))
				),
				[self._document(function)],
				['self=__module__'],
				self._writeFunctionArgumentsInit(function),
				#self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())) or ["pass"],
				"\n"
			]
		else:
			res = [
				self._document(function),
				"def %s (%s)" % (
					name,
					", ".join(map(self.write, function.getParameters()))
				),
				#self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())),
				"\n"
			]
		if function.getAnnotations("post"):
			res[0] = "__wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'self=__module__' )
			res.append("result = __wrapped__(__this__, **arguments)")
			res.append(self.writeFunctionPost(function))
			res.append("return result")
		return self._format(*res)

	def onBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			*(list(map(self.write, block.getOperations())))
		)

	def onParameter( self, param ):
		"""Writes a parameter element."""
		default = param.getDefaultValue()
		if default is None:
			res = "%s" % (param.getName())
		else:
			res = "%s=None" % (param.getName())
		if param.isRest(): res = "*" + res
		return res

	def onAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value="None"
		return self._format(
			self._document(element),
			"%s = %s" % (element.getName(), default_value)
		)

	def onClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		# FIXME: Resolution of variables must occur at class scope, not at
		# instance scope
		if default_value:
			res = "%s = %s" % (element.getName(), self.write(default_value))
		else:
			res = "%s = None" % (element.getName())
		return self._format(self._document(element), res)

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'None'
		return self._format(
			self._document(element),
			"%s = %s" % (element.getName(), default_value)
		)

	def _writeSpecificSymbol( self, symbolName ):
		if symbolName == "self":
			return "self"
		if symbolName == "target":
			return "self"
		elif symbolName == "Undefined":
			return "None"
		elif symbolName == "True":
			return "True"
		elif symbolName == "False":
			return "False"
		elif symbolName == "None":
			return "None"
		elif symbolName == "super":
			assert self.resolve("self")[0], "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			parents = self.getCurrentClassParents()
			if parents:
				absolute_name = self.getAbsoluteNameFromModule(parents[0], self.getCurrentModule())
				if not absolute_name:
					# In this case, it means we couldn't resolve the parent, so we'll just write it
					# as-is
					return parents[0].getReferenceName()
				else:
					return absolute_name
			else:
				return "%s.__bases__[0]" % (
					self.getAbsoluteNameFromModule(self.getCurrentClass(), self.getCurrentModule())
				)
		else:
			assert None

	SPECIFIC_SYMBOLS = "self target super Undefined True False None".split()

	def onReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		slot, value = self.resolve(symbol_name)
		scope = None
		ancestors = self.getCurrentClassAncestors() or []
		if slot:
			scope = slot.getDataFlow().getElement()
		if symbol_name in self.SPECIFIC_SYMBOLS:
			return self._writeSpecificSymbol(symbol_name)
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return "print "
			else: return symbol_name
		# It is a method of the current class
		elif self.getCurrentClass() == scope or scope in ancestors:
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "self.%s" % (symbol_name)
				else:
					return "self.%s " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				if self.isIn(interfaces.IInstanceMethod):
					return "self.__class__.%s" % (symbol_name)
				else:
					return "self.%s" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isIn(interfaces.IClassMethod):
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
			local_slot = self.getCurrentDataFlow().getParent().getSlot(symbol_name)
			self.resolve(symbol_name)
			if scope == self.getCurrentModule():
				return symbol_name
			names = [scope.getName(), symbol_name]
			cur_scope = scope
			while cur_scope.getParent():
				cur_scope = cur_scope.getParent()
				if cur_scope.hasName():
					names.insert(0, cur_scope.getName())
			return ".".join(names)
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassAncestors():
				return "self." + symbol_name
			# Otherwise it is an outside class, and we have to check that the
			# value is not an instance slot
			else:
				names = [scope.getName(), symbol_name]
				while scope.getParent():
					scope = scope.getParent()
					if scope.hasName():
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
				"is":"is",
				"is not":"!=",
				"not":"not",
				"or":"or"
	}
	def onOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = self.OPERATORS.get(o) or o
		return "%s" % (o)

	def onNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def onString( self, element ):
		"""Writes a string element."""
		s = element.getActualValue()
		return repr(s)

	def onList( self, element ):
		"""Writes a list element."""
		return '[%s]' % (", ".join([
			self.write(e) for e in element.getValues()
		]))

	def _writeDictKey( self, key ):
		if isinstance(key, interfaces.IString):
			return self.write(key)
		else:
			# FIXME: Raise an error, because JavaScript only allow strings as keys
			return "(%s)" % (self.write(key))

	def onDict( self, element ):
		return '{%s}' % (", ".join([
			"%s:%s" % ( self._writeDictKey(k),self.write(v))
			for k,v in element.getItems()
			])
		)

	def onAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		v = allocation.getDefaultValue()
		if v:
			return "%s=%s" % (s.getName(), self.write(v))
		else:
			return "%s" % (s.getName())

	def onAssignment( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			self.write(assignation.getTarget()),
			self.write(assignation.getAssignedValue())
		)

	def onEnumeration( self, operation ):
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

	def onResolution( self, resolution ):
		"""Writes a resolution operation."""
		resolved_name = resolution.getReference().getReferenceName()
		context       = resolution.getContext()
		if context:
			if isinstance(context, interfaces.IReference) and context.getReferenceName() == "super":
				return "(lambda *a,**kw:%s.%s(self,*a,**kw))" % (
					self.write(resolution.getContext()),
					resolved_name
				)
			# FIXME: Not sure what test case this is supposed to cover...
			#elif resolved_name == "super":
			#	t = self.write(resolution.getContext())
			#	return "(lambda *a,**kw:%s.__self__.__class__.__bases__[0].%s(%s.__self__))" % (t,t,t)
			elif resolution.getContext() == self.getCurrentModule():
				return "%s" % (resolved_name)
			else:
				return "%s.%s" % (self.write(resolution.getContext()), resolved_name)
		else:
			return "%s" % (resolved_name)

	def onComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = [x for x in computation.getOperands() if x!=None]
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
		if self.isIn(interfaces.IComputation):
			res = "(%s)" % (res)
		return res

	def _closureIsRewrite(self, closure):
		embed_templates_for_backend = []
		others = []
		if not isinstance(closure, interfaces.IClosure):
			return False
		for op in closure.getOperations():
			if isinstance(op, interfaces.IEmbedTemplate):
				lang = op.getLanguage().lower()
				if lang == "python":
					embed_templates_for_backend.append(op)
				continue
		if embed_templates_for_backend and not others:
			return embed_templates_for_backend
		else:
			return ()

	RE_TEMPLATE = re.compile("\$\{[^\}]+\}")
	def _rewriteInvocation(self, invocation, closure, template):
		arguments = tuple([self.write(a) for a in invocation.getArguments()])
		parameters = tuple([a.getName() for a  in closure.getParameters()])
		args = {}
		for i in range(len(arguments)):
			args[parameters[i]] = arguments[i]
		target = invocation.getTarget()
		# To have the 'self', the invocation target must be a resolution on an
		# object
		assert isinstance(target, interfaces.IResolution)
		args["self"] = "self_" + str(time.time()).replace(".","_") + str(random.randint(0,100))
		args["self_once"] = self.write(target.getContext())
		vars = []
		for var in self.RE_TEMPLATE.findall(template):
			var = var[2:-1]
			vars.append(var)
			if var[0] == "_":
				if var not in args:
					args[var] = "var_" + str(time.time()).replace(".","_") + str(random.randint(0,100))
		# FIXME: Ensure that all arguments are provided, otherwise there may
		# be a template error.
		return "%s%s" % (
			"self" in vars and "%s=%s\n" % (args["self"],self.write(args["self_once"])) or "",
			string.Template(template).substitute(args)
		)

	def onInvocation( self, invocation ):
		"""Writes an invocation operation."""
		self.inInvocation = True
		t = self.write(invocation.getTarget())
		if isinstance(invocation.getTarget(), interfaces.IReference):
			# In case the target of an invocation is super, then we
			# add the "__init__". Maybe we should also check that the
			# invocation happens within a constructor. Not sure though.
			if invocation.getTarget().getReferenceName() == "super":
				t += ".__init__(self,"
		# We add a paren in case we weren't re-defining a call
		if t[-1] != ",": t+= "("
		target_type = invocation.getTarget().getResultAbstractType()
		if target_type:
			concrete_type = target_type.concreteType()
			rewrite = self._closureIsRewrite(concrete_type)
		else:
			rewrite = None
		if rewrite:
			return self._rewriteInvocation(invocation, concrete_type, "\n".join([r.getCode() for r in rewrite]))
		else:
			self.inInvocation = False
			return "%s%s)" % (
				t,
				", ".join(map(self.write, invocation.getArguments()))
				)

	def onArgument( self, argument ):
		r = self.write(argument.getValue())
		if argument.isAsMap():
			return "**(%s)" % (r)
		elif argument.isAsList():
			return "*(%s)" % (r)
		elif argument.isByName():
			return "%s=(%s)" % (argument.getName(), r)
		else:
			return r

	def onInstanciation( self, operation ):
		"""Writes an invocation operation."""
		return "%s(%s)" % (
			self.write(operation.getInstanciable()),
			", ".join(map(self.write, operation.getArguments()))
		)

	def _writeSelectionInExpression( self, selection ):
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

	def onSelection( self, selection ):
		# If we are in an assignataion and allocation which is contained in a
		# closure (because we can have a closure being assigned to something.)
		if self.isIn(interfaces.IAssignment) > self.isIn(interfaces.IClosure) \
		or self.isIn(interfaces.IAllocation) > self.isIn(interfaces.IClosure):
			return self._writeSelectionInExpression(selection)
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
					[process],
				)
			else:
				rule_code = (
					"elif %s:" % (self.write(rule.getPredicate())),
					[process],
				)
			result.extend(rule_code)
		return self._format(*result)

	def onIteration( self, iteration ):
		"""Writes a iteration operation."""
		it_name = self._unique("_iterator")
		iterator = iteration.getIterator()
		closure  = iteration.getClosure()
		args  = [a.getName() for a in closure.getParameters()]
		if len(args) == 0: args.append("__iterator_value")
		if len(args) == 1: args.append("__iterator_index")
		i = args[1]
		v = args[0]
		return self._format(
				"for %s in %s:" % (v, self.write(iterator)),
				list(map(self.write, closure.getOperations()))
		)


	def onRepetition( self, repetition ):
		return self._format(
			"while %s:" % (self.write(repetition.getCondition())),
			[self.write(repetition.getProcess()) or "pass"]
		)

	def onAccessOperation( self, operation ):
		return self._format(
			"%s[%s]" % (self.write(operation.getTarget()), self.write(operation.getIndex()))
		)

	def onSliceOperation( self, operation ):
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

	def onEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def onTermination( self, termination ):
		"""Writes a termination operation."""
		evaluable = termination.getReturnedEvaluable()
		if isinstance(evaluable, interfaces.IInvocation):
			t = evaluable.getTarget()
			# Assert in Python is not a function
			if isinstance(t, interfaces.IReference) and t.getName() == "assert":
				return "%s" % ( self.write(evaluable))
		return "return %s" % ( self.write(evaluable))

	def onNOP( self, nop ):
		return "pass"

	def onBreaking( self, breaking ):
		"""Writes a break operation."""
		return "break"

	def onExcept( self, exception ):
		"""Writes a except operation."""
		return "raise " + self.write(exception.getValue())

	def onInterception( self, interception ):
		"""Writes an interception operation."""
		try_block   = interception.getProcess()
		try_catch   = interception.getIntercept()
		try_finally = interception.getConclusion()
		res         = ["try:", list(map(self.write, try_block.getOperations()))]
		if try_catch:
			res.extend([
				"except Exception as %s:" % ( self.write(try_catch.getArguments()[0])) ,
				list(map(self.write, try_catch.getOperations()))
			])
		if try_finally:
			res.extend(["finally:", list(map(self.write, try_finally.getOperations()))])
		return self._format(*res)

	def onImportSymbolOperation( self, element ):
		res = ["import"]
		res.append(element.getImportedElement())
		symbol_origin = element.getImportOrigin()
		symbol_alias = element.getAlias()
		if symbol_origin:
			vres = ["from", symbol_origin]
			vres.extend(res)
			res = vres
		if symbol_alias:
			res.extend(["as", symbol_alias])
		return " ".join(res)

	def onImportSymbolsOperation( self, element ):
		res = ["import"]
		res.append(", ".join(element.getImportedElements()))
		symbol_origin = element.getImportOrigin()
		if symbol_origin:
			vres = ["from", symbol_origin]
			vres.extend(res)
			res = vres
		return " ".join(res)

	def onImportModuleOperation( self, element ):
		res = ["import"]
		res.append(element.getImportedModuleName())
		symbol_alias = element.getAlias()
		if symbol_alias:
			res.extend(["as", symbol_alias])
		return " ".join(res)

	def onImportModulesOperation( self, element ):
		res = ["import"]
		res.append(", ".join(element.getImportedModuleNames()))
		return " ".join(res)

	def onEmbed( self, embed ):
		lang = embed.getLanguage().lower().strip()
		if not lang in self.supportedEmbedLanguages:
			self.environment.report.error ("Python writer cannot embed language:", lang)
			res = [ "# Unable to embed the following code" ]
			for l in embed.getCode().split("\n"):
				res.append("# " + l)
			return "\n".join(res)
		else:
			return embed.getCode()

	def _document( self, element ):
		if element.getDocumentation():
			doc = element.getDocumentation()
			return '"""%s"""' % (doc.getContent().replace('"""', '\\"\\"\\"'))
		else:
			return None

	def write( self, element ):
		#if isinstance(element, interfaces.IOperation):
		#	print "OPERATION", element.__class__
		return AbstractWriter.write(self, element)

MAIN_CLASS = Writer
# EOF - vim: tw=80 ts=4 sw=4 noet
