#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 05-Jul-2006
# Last mod  : 07-Dec-2007
# -----------------------------------------------------------------------------

from lambdafactory.modelwriter import AbstractWriter, flatten
import lambdafactory.interfaces as interfaces
import lambdafactory.reporter as reporter
from lambdafactory.splitter import SNIP
import os.path,re,time,string, random

# TODO: Pnuts does not really support absolute reference names, so maybe
# when importing, we should consider java_awt_Frame instead of java.awt.Frame

#------------------------------------------------------------------------------
#
#  Pnuts Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	def __init__( self ):
		AbstractWriter.__init__(self)
		self.jsPrefix = ""
		self.jsCore   = "Extend."
		self.supportedEmbedLanguages = ["pnuts"]
		self.inInvocation = False

	def getRuntimeSource(s):
		"""Returns the Pnuts code for the runtime that is necassary to run
		the program."""
		this_file = os.path.abspath(__file__)
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

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "init"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name

	def onModule( self, moduleElement):
		"""Writes a Module element."""
		pnuts_name = self.getAbsoluteName(moduleElement)
		# TODO: Move imports to the top
		module_slots = moduleElement.getSlots()
		code = ['package("%s");' % (pnuts_name)]
		for i in moduleElement.getImportOperations():
			code.append(self.write(i))
		for name, value in module_slots:
			if isinstance(value, interfaces.IModuleAttribute):
				code.append("%s = %s" % (moduleElement.getName(), self.write(value)))
			elif isinstance(value, interfaces.IClass):
				code.append(self.write(value))
			elif isinstance(value, interfaces.IFunction):
				if value.getName() == interfaces.Constants.ModuleInit:
					imports = []
					operations = []
					for op in value.getOperations():
						if isinstance(op,interfaces.IImportOperation):
							imports.append(op)
						else:
							operations.append(op)
					code.extend(map(self.write, operations))
					if imports:
						imports.insert(0, "")
						imports.append("")
					code.insert(1,map(self.write, imports))
				else:
					code.append(self.write(value))
			else: 
				code.append("%s=%s" % (self.renameModuleSlot(name), self.write(value)))
		return self._format(
			*code
		)

	def onClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getParentClasses()
		parent  = None
		if len(parents) == 1:
			parent = self.write(parents[0])
		elif len(parents) > 1:
			raise Exception("Pnuts back-end only supports single inheritance")
		# We create a map of class methods, including inherited class methods
		# so that we can copy the implementation of these
		classOperations = {}
		for name, meths in classElement.getInheritedClassMethods().items():
			# FIXME: Maybe use wrapper instead
			classOperations[name] = self._writeClassMethodProxy(classElement, meths)
		# Here, we've got to cheat a little bit. Each class method will 
		# generate an '_imp' suffixed method that will be invoked by the 
		for meth in classElement.getClassMethods():
			classOperations[meth.getName()] = meth
		classOperations = classOperations.values()
		classAttributes = {}
		for name, attribute in classElement.getInheritedClassAttributes().items():
			classAttributes[name] = self.write(attribute)
		for attribute in classElement.getClassAttributes():
			classAttributes[attribute.getName()] = self.write(attribute)
		classAttributes = classAttributes.values()
		result = []
		result.append(self._document(classElement))
		result.append("class %s" % (classElement.getName()))
		if parent:
			result[-1] = result[-1] + " extends %s" % (parent)
		# We collect class attributes
		attributes   = classElement.getAttributes()
		constructors = classElement.getConstructors()
		destructors  = classElement.getDestructors()
		methods      = classElement.getInstanceMethods()
		if False and classAttributes:
			written_attrs = ",\n".join(map(self.write, classAttributes))
			result.append("shared:{")
			result.append([written_attrs])
			result.append("},")
		if False and classOperations:
			written_ops = ",\n".join(map(self.write, classOperations))
			result.append("operations:{")
			result.append([written_ops])
			result.append("},")
		content = []
		if attributes:
			content.extend(map(self.write, attributes))
		if constructors:
			assert len(constructors) == 1, "Multiple constructors are not supported yet"
			content.append(self.write(constructors[0]))
		if destructors:
			assert len(destructors) == 1, "Multiple destructors are not supported"
			content.append(self.write(destructors[0]))
		if methods:
			content.extend(map(self.write, methods))
		result.append("{")
		result.append(content)
		result.append("}")
		return self._format(result)

	def onMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		return self._format(
			self._document(methodElement),
			"%s(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			["__this__=this"],
			self._writeClosureArguments(methodElement),
			self._writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def onClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		args        = methodElement.getArguments()
		return self._format(
			self._document(methodElement),
			"function %s_%s(%s){" % (self.getCurrentClass().getName(),method_name, ", ".join(map(self.write, args))),
			["__this__ = this"],
			self._writeClosureArguments(methodElement),
			self._writeFunctionWhen(methodElement),
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
			["return %s.%s.apply(%s, arguments)" % (
				self.getAbsoluteName(inheritedMethodElement.getParent()),
				method_name,
				self.getAbsoluteName(currentClass)
			)],
			'}'
		)

	def onConstructor( self, element ):
		"""Writes a method element."""
		current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("__this__.%s = %s" % (a.getName(), self.write(a.getDefaultValue())))
		return self._format(
			self._document(element),
			"%s(%s){" % (
				current_class.getName(),
				", ".join(map(self.write, element.getArguments()))
			),
			["__this__=this"],
			self._writeClosureArguments(element),
			attributes or None,
			map(self.write, element.getOperations()),
			"}"
		)

	def onClosure( self, closure ):
		"""Writes a closure element."""
		return self._format(
			self._document(closure),
			"{%s -> " % ( ", ".join(map(self.write, closure.getArguments()))),
			self._writeClosureArguments(closure),
			map(self.write, closure.getOperations()),
			"}"
		)
	
	def onClosureBody(self, closure):
		return self._format('{', map(self.write, closure.getOperations()), '}')

	def _writeClosureArguments(self, closure):
		i = 0
		l = len(closure.getArguments())
		result = []
		for argument in closure.getArguments():
			if argument.isRest():
				assert i >= l - 2
				result.append("%s = %s(arguments,%d)" % (
					argument.getName(),
					self.jsPrefix + self.jsCore + "sliceArguments",
					i
				))
			i += 1
		return result

	def _writeFunctionWhen(self, function ):
		res = []
		for a in function.getAnnotations("when"):
			res.append("if (!(%s)) {return}" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunctionPost(self, function ):
		res = []
		for a in function.getAnnotations("post"):
			res.append("if (!(%s)) {throw new Exception('Assertion failed')}" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName()

		args = []
		for arg in function.getArguments():
			args.append(self.write(arg))
		args = ", ".join(args)
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"function %s(%s) {" % (
					function.getName(),
					args
				),
				[self._document(function)],
				self._writeClosureArguments(function),
				self._writeFunctionWhen(function),
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
				self._writeFunctionWhen(function),
				map(self.write, function.getOperations()),
				"}"
			]
		if function.getAnnotations("post"):
			res[0] = "__wrapped__ = " + res[0] + ""
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, '__this__=%s' % (self.getAbsoluteName(parent)))
			res.append("result = __wrapped__.apply(__this__, arguments)")
			res.append(self.writeFunctionPost(function))
			res.append("return result")
		return self._format(res)

	def onBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			"{",
			map(self.write, block.getOperations()),
			"}"
		)

	def onArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s" % (
			argElement.getName(),
		)

	def onAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			return self._format(
				self._document(element),
				"%s = %s" % (element.getName(), default_value)
			)
		else:
			return self._format(
				self._document(element),
				"Object %s" % (element.getName())
			)

	def onClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			res = "%s:%s" % (element.getName(), self.write(default_value))
		else:
			res = "%s:undefined" % (element.getName())
		return self._format(self._document(element), res)

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'undefined'
		return self._format(
			self._document(element),
			"%s=%s" % (element.getName(), default_value)
		)

	def onReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		slot, value = self.resolve(symbol_name)
		if slot:
			scope = slot.getDataFlow().getElement()
		else:
			scope = None
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
			return "super"
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return "System.out.println"
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
				if self.isIn(interfaces.IInstanceMethod):
					return "__this__.getClass().%s" % (symbol_name)
				else:
					return "__this__.%s" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isIn(interfaces.IClassMethod):
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
			# FIXME: We should check that the symbol was imported before
			return symbol_name
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassAncestors():
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

	PNUTS_OPERATORS = {
				"and":"&&",
				"is":"==",
				"is not":"!=",
				"not":"!",
				"or":"||"
	}
	def onOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = self.PNUTS_OPERATORS.get(o) or o
		return "%s" % (o)

	def onNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def onString( self, element ):
		"""Writes a string element."""
		return '"%s"' % (element.getActualValue().replace('"', '\\"'))

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
		# TODO: Rule: keys have to be strings
		return '{%s}' % (", ".join([
			"%s=>%s" % ( self._writeDictKey(k),self.write(v))
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

	def onAssignation( self, assignation ):
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
		res = self.jsPrefix + self.jsCore + "range(%s,%s)" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self._write(step)
		return res

	def onResolution( self, resolution ):
		"""Writes a resolution operation."""
		resolved_name = resolution.getReference().getReferenceName()
		if resolution.getContext():
			if resolved_name == "super":
				return "%s.super" % (self.write(resolution.getContext()))
			else:
				return "%s.%s" % (self.write(resolution.getContext()), resolved_name)
		else:
			return "%s" % (resolved_name)

	def onComputation( self, computation ):
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
		if self.isIn(interfaces.IComputation):
			res = "(%s)" % (res)
		return res

	def onInvocation( self, invocation ):
		"""Writes an invocation operation."""
		self.inInvocation = True
		t = self.write(invocation.getTarget())
		self.inInvocation = False
		return "%s(%s)" % (
			t,
			", ".join(map(self.write, invocation.getArguments()))
		)
	
	def onInstanciation( self, operation ):
		"""Writes an invocation operation."""
		return "new %s(%s)" % (
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
			text += "((%s) ? (%s) : " % (
				self.write(rule.getPredicate()),
				self.write(expression)
			)
		text += "undefined"
		for r in rules:
			text += ")"
		return text
	
	def onSelection( self, selection ):
		# If we are in an assignataion and allocation which is contained in a
		# closure (because we can have a closure being assigned to something.)
		if self.isIn(interfaces.IAssignation) > self.isIn(interfaces.IClosure) \
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

	def onIteration( self, iteration ):
		"""Writes a iteration operation."""
		it_name = self._unique("_iterator")
		args = map(self.write, iteration.getClosure().getArguments())
		if not args:
			args = ["_V_"]
		assert len(args) == 1
		return self._format(
			"for (%s : %s ){" % (
				args[0],
				self.write(iteration.getIterator()),
			),
			map(self.write,iteration.getClosure().getOperations()),
			"}"

		)

	def onRepetition( self, repetition ):
		return self._format(
			"while (%s)" % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess())
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
		else: end = "undefined"
		return self._format(
			"S.Core.slice(%s,%s,%s)" % (
				self.write(operation.getTarget()),
				start,
				end
		))

	def onEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def onTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def onBreaking( self, breking ):
		"""Writes a break operation."""
		return "break"

	def onExcept( self, exception ):
		"""Writes a except operation."""
		return "throw (" + self.write(exception.getValue()) + ")"
	
	def onInterception( self, interception ):
		"""Writes an interception operation."""
		try_block   = interception.getProcess()
		try_catch   = interception.getIntercept()
		try_finally = interception.getConclusion()
		res         = ["try {", map(self.write, try_block.getOperations()), "}"]
		if try_catch:
			res.insert(1,[
				"catch( Exception, function(%s){" % ( self.write(try_catch.getArguments()[0])) ,
				map(self.write, try_catch.getOperations()),
				"})"
			])
		if try_finally:
			res.extend(["finally {", map(self.write, try_finally.getOperations()), "}"])
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
		return [";".join(res)]

	def onImportSymbolsOperation( self, element ):
		res = []
		symbol_origin = element.getImportOrigin()
		for e in element.getImportedElements():
			res.append('import("%s.%s")' % (symbol_origin, e))
		return [";".join(res)]

	def onImportModuleOperation( self, element ):
		module_name = element.getImportedModuleName()
		symbol_alias = element.getAlias()
		if symbol_alias:
			symbol_name = module_name.split(".")[-1]
			if symbol_name != symbol_alias:
				return ['import("%s") ; %s = %s' % ( module_name, symbol_alias, symbol_name)]
			else:
				return ['import("%s")' % ( module_name)]
		else:
			return ['import("%s")' %  (module_name)]

	def onImportModulesOperation( self, element ):
		res = []
		for m in element.getImportedModuleNames():
			res.append("import " + m)
		return ";".join(res)

	def onEmbed( self, embed ):
		lang = embed.getLanguage().lower().strip()
		if not lang in self.supportedEmbedLanguages:
			self.environment.report.error ("Pnuts writer cannot embed language:", lang)
			res = [ "// Unable to embed the following code" ]
			for l in embed.getCode().split("\n"):
				res.append("// " + l)
			return "\n".join(res)
		else:
			return embed.getCode()

	def _document( self, element ):
		if element.getDocumentation():
			doc = element.getDocumentation()
			res = []
			for line in doc.getContent().split("\n"):
				res.append("// " + line)
			return "\n".join(res)
		else:
			return None

MAIN_CLASS = Writer

# EOF
