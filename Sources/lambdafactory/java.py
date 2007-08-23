#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 30-May-2007
# Last mod  : 02-Jun-2007
# -----------------------------------------------------------------------------

from modelwriter import AbstractWriter, flatten
from resolver import AbstractResolver
import interfaces, reporter

class Resolver(AbstractResolver):
	pass

#------------------------------------------------------------------------------
#
#  Java Runtime Writer
#
#------------------------------------------------------------------------------

class RuntimeWriter:

	def __init__(self, writer):
		self.writer = writer
		self.write  = self.writer.write
		self.p = self.prefix = "lambdafactory"

	#--------------------------------------------------------------------------
	# RENAMING
	#--------------------------------------------------------------------------

	def className( self, name ):
		"""Normalizes the given name to be like a class name"""
		return "".join(n[0].upper() + n[1:] for n in name.split("_"))

	def moduleName( self, name ):
		"""Normalizes the given name to be like a module name"""
		return "".join(n[0].upper() + n[1:] for n in name.split("_"))

	#--------------------------------------------------------------------------
	# RUNTIME CLASSES
	#--------------------------------------------------------------------------

	def moduleClass( self ):
		return "%s.Class" % (self.p)

	def objectClass( self ):
		return "%s.Object" % (self.p)

	def valueClass( self ):
		return "java.lang.Object" 

	def op( self, name ):
		return "%s.Runtime.%s"  % (self.prefix, name)

	def compute( self, operator ):
		if operator == "+":
			op = "Add"
		elif operator == "-":
			op = "Substract"
		elif operator == "/":
			op = "Divide"
		elif operator == "*":
			op = "Multiply"
		else:
			raise Exception("Unsupported operator for the Java back-end: %s" % (operator))
		return self.op("compute" + op)

	#--------------------------------------------------------------------------
	# RUNTIME OPERATION
	#--------------------------------------------------------------------------

	
	def new(self, classElement):
		return "NEW0(%s)" % (self.writer.getAbsoluteName(classElement)) 
	
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

	def typeFor(self, element):
		if isinstance(element, interfaces.IModule):
			return "SgModule*"
		elif isinstance(element, interfaces.IClass):
			return "SgClass*"
		else:
			return "SgValue"

	def slice(self, target, slice):
		return self.op("slice(%s,%s)" % (
			self.write(operation.getTarget()),
			self.write(operation.getSlice())
		))

#------------------------------------------------------------------------------
#
#  Java Source Code Writer
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	def __init__( self, reporter=reporter.DefaultReporter ):
		AbstractWriter.__init__(self, reporter)
		self.resolver = Resolver(reporter=reporter)
		self.inInvocation = False
		self.runtime = self.rt = RuntimeWriter(self)
		self.closureCounter = 0
		self.accumulator = []
	
	def accumulate(self, code):
		"""Accumulates code that will be dumped and flush when the 'dump' method
		is called. This is specific to the C back-end and allows doing all kind
		of stuff in the module initialization phase"""
		self.accumulator.append(code)
	
	def dump(self):
		"""Returns the content of the accummulator (as a list) and empties
		it."""
		res = self.accumulator
		self.accumulator=[]
		return res

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
			if isinstance(element, interfaces.IModule):
				names.insert(0, self.rt.moduleName(element.getName()))
			elif isinstance(element, interfaces.IClass):
				names.insert(0, self.rt.className(element.getName()))
			elif not isinstance(element, interfaces.IProgram):
				names.insert(0, element.getName())
		return ".".join(names)

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "initialize"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name

	def writeModule( self, moduleElement, contentOnly=False ):
		"""Writes a Module element."""
		code = [
		]
		for slot, value in moduleElement.getSlots():
			res = self.write(value)	
			if type(res) in (unicode,str):
				code.append(res)
			else:
				code.extend(res)
		code = [
			'public class %s extends %s {' % (
			self.rt.moduleName(moduleElement.getName()),self.rt.moduleClass()),
			code,
			["public static void init() {",
			self.dump(),
			"}"
			],
			"}"
		]
		return self._format(
			*code
		)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		parent  = self.rt.objectClass()
		class_name = self.rt.className(classElement.getName())
		if len(parents) == 1:
			parent = self.write(parents[0])
			parent = parent[:-len(".class")]
		elif len(parents) > 1:
			raise Exception("Java back-end only supports single inheritance")
		return self._format(
			"public static class %s extends %s {" % (class_name, parent),
				[	self._document(classElement),
					"\n".join(map(self.write, flatten(
					classElement.getClassAttributes(),
					classElement.getAttributes(),
					classElement.getConstructors(),
					classElement.getDestructors(),
					classElement.getClassMethods(),
					classElement.getInstanceMethods()
				)))],
			"}\n"
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		if method_name == interfaces.Constants.Constructor: method_name = "initialize"
		if method_name == interfaces.Constants.Destructor:  method_name = "destroy"
		return self._format(
			self._document(methodElement),
			"public %s %s(%s){" % (
				self.rt.valueClass(),
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			self.writeFunctionWhen(methodElement),
			map(self.writeStatement, methodElement.getOperations()),
			[self.writeImplicitReturn(methodElement)],
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		return self._format(
			self._document(methodElement),
			"public static %s %s(%s){" % (
				self.rt.valueClass(),
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			self.writeFunctionWhen(methodElement),
			map(self.writeStatement, methodElement.getOperations()),
			[self.writeImplicitReturn(methodElement)],
			"}"
		)

	def writeConstructor( self, element ):
		"""Writes a method element."""
		current_class = self.getCurrentClass()
		attributes    = []
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("this.%s = %s(%s);" % (
				a.getReferenceName(),
				self.rt.op("box"),
				self.write(a.getDefaultValue()))
			)
		return self._format(
			self._document(element),
			"public %s(%s){" % (
				self.rt.className(current_class.getName()),
				", ".join(map(self.write, element.getArguments()))
			),
			attributes or None,
			map(self.writeStatement, element.getOperations()),
			"}"
		)

	def writeImplicitReturn( self, function ):
		if not function.endsWithTermination():
			return "return null;"
		else:
			return ""

	def writeClosure( self, closure ):
		"""Writes a closure element."""
		return self._format(
			"new org.sugarlang.runtime.Closure {",
			[
				", ".join(map(self.write, closure.getArguments()))
			],
			map(self.writeStatement, closure.getOperations()),
			"}"
		)

	def writeClosureBody(self, closure):
		return self._format('{', map(writeStatement, closure.getOperations()), '}')

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
		result = self.rt.valueClass()
		args   = ", ".join(map(self.write, function.getArguments()))
		returns = [self.writeImplicitReturn(function)]
		if name == interfaces.Constants.MainFunction:
			name = "main"
			result = "void"
			args = "String[] args"
			returns = ()
		elif name == interfaces.Constants.ModuleInit:
			name = "moduleInit"
			result = "void"
			returns = ()
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				"public static %s %s (%s){" % (
					result,
					name,
					args,
				),
				[self._document(function)],
				self.writeFunctionWhen(function),
				map(self.writeStatement, function.getOperations()),
				returns,
				"}"
			]
			return res
		else:
			args = []
			i    = 0
			for a in function.getArguments():
				args.append("java.lang.Object %s=%s(args[%s]);" % (
					a.getReferenceName(),
					self.rt.op("box"),
					i
				))
				i += 1
			res = [
				"new %s() { public java.lang.Object do(java.lang.Object[] args) {" % (self.rt.op("Closure")),
				args,
				map(self.writeStatement, function.getOperations()),
				"}}"
			]
			return res

	def writeBlock( self, block ):
		"""Writes a block element."""
		return self._format(
			"{",
			map(self.write, block.getOperations()),
			"}"
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s %s" % (
			self.rt.valueClass(),
			argElement.getReferenceName(),
		)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		return self._format(
			self._document(element),
			'public %s %s;' % (
				self.rt.valueClass(),
				element.getReferenceName()
			)
		)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		class_name = self.getAbsoluteName(self.getCurrentClass())
		if default_value:
			return "public static %s %s = (%s)%s(%s);" % (
				self.rt.valueClass(),
				element.getReferenceName(),
				self.rt.valueClass(),
				self.rt.op("box"),
				self.write(default_value)
			)
		else:
			return "public static %s %s;" % (
				self.rt.valueClass(),
				element.getReferenceName()
			)

	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		value, scope      = self.resolve(symbol_name)
		if scope and scope.hasSlot(symbol_name):
			value = scope.getSlot(symbol_name)
		if symbol_name == "self":
			return "this"
		elif symbol_name == "super":
			assert self.resolve("this"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			return "super"
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print":
				return '%s(lambdafactory.Runtime.class,"print")' % (self.rt.op("resolve"))
			else:
				return symbol_name
		# It is a method/property of the current class
		elif self.getCurrentClass() == scope:
			if isinstance(value, interfaces.IInstanceMethod):
				return "Runtime.resolveMethod(this,'%s')" % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				return "Runtime.resolveClassMethod(this,'%s')" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				return "%s" % (symbol_name)
			else:
				assert isinstance(value, interfaces.IAttribute)
				return "%s" % (symbol_name)
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
			# In Java, you cannot reference classes directly, so if you have
			# class 'org.pouet.MyClass' you have to reference it by using
			# 'org.pouet.MyClass.class'
			if isinstance(value, interfaces.IClass):
				names.append("class")
			return ".".join(names)
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassAncestors():
				return "$G(self,%s)" % (symbol_name)
			# Otherwise it is an outside class, and we have to check that the
			# value is not an instance slot
			else:
				names = [scope.getName()]
				while scope.getParent():
					scope = scope.getParent()
					names.insert(0, scope.getName())
				return "$G(%s,%s)" % ("_".join(names), symbol_name)
		# FIXME: This is an exception... iteration being an operation, not a
		# context...
		elif isinstance(scope, interfaces.IIteration):
			return symbol_name
		elif isinstance(scope, interfaces.IClosure):
			return symbol_name
		else:
			raise Exception("Unsupported scope:" + str(scope))

	JAVA_OPERATORS = {
				"and":"&&",
				"is":"==",
				"is not":"!=",
				"not":"!",
				"or":"||"
	}
	def writeOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = self.JAVA_OPERATORS.get(o) or o
		return "%s" % (o)

	def writeNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def writeString( self, element ):
		"""Writes a string element."""
		return '"%s"' % (element.getActualValue().replace('"', '\\"'))

	def writeList( self, element ):
		"""Writes a list element."""
		return '%s(new Object[] [%s])' % (self.op("list"),
			", ".join([ self.write(e) for e in element.getValues()]))

	def writeDictKey( self, key ):
		if isinstance(key, interfaces.IString):
			return self.write(key)
		else:
			# FIXME: Raise an error, because JavaScript only allow strings as keys
			return "(%s)" % (self.write(key))

	def writeDict( self, element ):
		return '%s(%s)' % (self.rt.op("dict"),
			", ".join([
				"%s:%s" % ( self.writeDictKey(k),self.write(v))
				for k,v in element.getItems()
			])
		)
		
	def writeAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		v = allocation.getDefaultValue()
		if v:
			return "%s %s=%s(%s)" % (
				self.rt.valueClass(),
				s.getReferenceName(),
				self.rt.op("box"),
				self.write(v)
			)
		else:
			return "%s %s" % (
				self.rt.valueClass(),
				s.getReferenceName()
			)

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s(%s)" % (
			self.write(assignation.getTarget()),
			self.rt.op("box"),
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
		res = "%s(%s,%s)" % (self.rt.op("range"), start, end)
		step = operation.getStep()
		if step: res += " step " + self._write(step)
		return res

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		if resolution.getContext():
			return '%s(%s,"%s")' % (self.rt.op("resolve"),self.write(resolution.getContext()), resolution.getReference().getReferenceName())
		else:
			return "%s" % (resolution.getReference().getReferenceName())

	def isLiteral( self, element ):
		if isinstance( element, interfaces.IComputation ):
			for o in element.getOperands():
				if not self.isLiteral(o):
					return False
			return True
		else:
			return isinstance(element, interfaces.ILiteral)

	def writeComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = filter(lambda x:x!=None,computation.getOperands())
		operator = computation.getOperator()
		# FIXME: Add rules to remove unnecessary parens
		if len(operands) == 1:
			operand = operands[0]
			if self.isLiteral(operand):
				res = "%s %s" % (
					self.write(operator),
					self.write(operand)
				)
			else:
				res = "%s(%s)" % (
					self.rt.compute(self.write(operator)),
					self.write(operand)
				)
		else:
			a = operands[0]
			b = operands[1]
			if self.isLiteral(computation):
				res = "%s %s %s" % (
					self.write(operands[0]),
					self.write(operator),
					self.write(operands[1])
				)
			else:
				res = '%s(%s,%s)' % (
					self.rt.compute(self.write(operator)),
					self.write(operands[0]),
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
		if t == "super":
			return "super(%s)" % (
				", ".join(map(self.write, invocation.getArguments()))
			)
		else:
			return "%s(%s, new Object[]{%s})" % (
				self.rt.op("invoke"),
				t,
				", ".join(map(self.write, invocation.getArguments()))
			)
	
	def writeInstanciation( self, operation ):
		"""Writes an invocation operation."""
		len_args = len(operation.getArguments())
		class_name = self.write(operation.getInstanciable())
		assert class_name.endswith(".class")
		class_name = class_name[:-len(".class")]
		if len_args == 0:
			return "new %s()" % (class_name)
		else:
			return "new %s(%s)" % (
				class_name,
				", ".join("%s(%s)" % (self.rt.op("box"),self.write(a)) for a in operation.getArguments())
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
			self.rt.op("iterate(%s,") % (self.write(iteration.getIterator())),
			self.write(iteration.getClosure()),
			")"
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
		return "return %s(%s)" % (
			self.rt.op("box"),
			self.write(termination.getReturnedEvaluable())
		)

	def writeStatement(self, *args):
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
