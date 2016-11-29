# Encoding: ISO-8859-1
# vim: ts=4 tw=79 noet

from . import typecast, interfaces

# This is not very pretty, but the typer module will populate the catalog
# with the types parsed from the library. The "typeForValue" operation will
# then use the catalog to resolve specific types (like List, Dict, etc)
CATALOG = None

class TypeCollection:
	"""A type collection is a class that contains type definitions which can be
	easily retrieved using the @getType method."""

	@classmethod
	def getType( cls, name ):
		"""Returns the type with the given name, or None if it does not
		exist."""
		keys = dir()
		if name in keys:
			return getattr(cls, name)
		else:
			return None

class Data(TypeCollection):pass
class Operations(TypeCollection): 	pass
class Structure(TypeCollection): pass
class Behaviour(TypeCollection): pass
class Runtime(TypeCollection): pass
COLLECTIONS = (Data, Operations, Structure, Behaviour, Runtime)

# This is the list of abstract types

Nil                            = typecast.Nil
Nothing                        = typecast.Nothing
Any                            = typecast.Any
Rest                           = typecast.Rest
Unresolved                     = typecast.Unresolved

Data.Char                      = typecast.Cell(typecast.bits(8))
Data.Integer                   = typecast.Cell(typecast.bits(32))
Data.UnsignedInteger           = typecast.Cell(typecast.bits(32))
Data.Long                      = typecast.Cell(typecast.bits(64))
Data.Float                     = typecast.Cell(typecast.bits(32))
Data.Double                    = typecast.Cell(typecast.bits(64))
Data.String                    = typecast.Array(Data.Char)

Operations.Operation           = typecast.Context("Operation")
Operations.Computation         = Operations.Operation.subtype("Computation")
Operations.Casting             = Operations.Operation.subtype("Casting")
Operations.Allocation          = Operations.Operation.subtype("Allocation")

Structure.Context              = typecast.Context("Context")
Structure.Program              = Structure.Context.subtype("Program")
Structure.Module               = Structure.Context.subtype("Module")
Structure.Class                = Structure.Context.subtype("Class")
Structure.Interface            = Structure.Context.subtype("Interface")

Behaviour.Closure              = typecast.Process()
Behaviour.Function             = typecast.Process()
Behaviour.Method               = typecast.Process()

Runtime.Instance               = typecast.Context()

def typeForValue( value, noneIs=Nothing ):
	"""Associates a type with the given value. This basically creates a typecast
	instance/subtype, using the types defined in this module, using the given
	value which is a program element (implements interfaces defined in
	LF 'interfaces' module)."""
	res = None
	if value is None:
		return noneIs
	if hasattr(value, "_lf_type"): return value._lf_type
	if isinstance(value, interfaces.IOperation):
		res = Operations.getType(value.__class__.__name__)
		res = Any
	elif isinstance(value, interfaces.IModule):
		res = Structure.Module.clone()
	elif isinstance(value, interfaces.IClass):
		res = Structure.Class.clone()
		res.setName(value.getName())
	elif isinstance(value, interfaces.IInterface):
		res = Structure.Interface.clone()
		res.setName(value.getName())
	elif isinstance(value, interfaces.IFunction):
		res = Behaviour.Function.clone()
	elif isinstance(value, interfaces.IClosure):
		res = Behaviour.Closure.clone()
	elif isinstance(value, interfaces.IArgument):
		default = value.getDefaultValue()
		if default is None: res = Any
		else: res = typeForValue(default, Any)
	elif isinstance(value, interfaces.IAttribute):
		default = value.getDefaultValue()
		if default is None: res = Any
		else: res = typeForValue(default, Any)
	elif isinstance(value, interfaces.IReference):
		res = Any
	elif isinstance(value, interfaces.IList):
		list_interface = CATALOG.get("DataTypes.List")
		res = typeForValue(list_interface)
	elif isinstance(value, interfaces.IDict):
		map_interface = CATALOG.get("DataTypes.Map")
		res = typeForValue(map_interface)
	elif isinstance(value, interfaces.IString):
		map_interface = CATALOG.get("DataTypes.String")
		res = typeForValue(map_interface)
	elif isinstance(value, interfaces.INumber):
		res = Any
	if res is None:
		return
		#raise Exception("No abstract type for Python value: %s" % (value))
	# When the type is a context, we populate its slots
	if isinstance(value, interfaces.IClosure):
		# We add the arguments
		for arg in value.getArguments():
			res.add(typeForValue(arg))
		# We add the return type (Any by default)
		# FIXME: We should constrain the types at a later point
		res.add(Any)
	if isinstance(value, interfaces.IContext):
		assert isinstance(res, typecast.Context) or isinstance(res, typecast.Process)
		for slot, slot_value in value.getSlots():
			res.set(slot, typeForValue(slot_value))
	# We cache the abstract type
	value._lf_type = res
	res.setConcreteType(value)
	return res

# EOF
