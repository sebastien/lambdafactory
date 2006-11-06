# Encoding: ISO-8859-1
# vim: ts=4 tw=79 noet 

import typecast, interfaces

class TypeCollection:
	"""A type collection is a class that contains type definitions which can be
	easily retrieved using the @getType method."""

	@classmethod
	def getType( self, name ):
		"""Returns the type with the given name, or None if it does not
		exist."""
		keys = dir()
		if name in keys:
			return getattr(self, name)
		else:
			return None

class Data(TypeCollection):pass
class Operations(TypeCollection): 	pass
class Structure(TypeCollection): pass
class Behaviour(TypeCollection): pass
class Runtime(TypeCollection): pass
COLLECTIONS = (Data, Operations, Structure, Behaviour, Runtime)

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

Behaviour.Function             = typecast.Process()
Behaviour.Method               = typecast.Process()

Runtime.Instance               = typecast.Context()

def typeFromClass( aclass ):
	"""Returns the modeltype corresponding to the given Python model class.
	This allows to bridge types from the Python model implementation to the
	abstract typecast-based typesystem.
	
	This function will raise an execption if the type is not defined."""
	name = aclass.__name__
	if interfaces.implements(aclass, interfaces.IOperation):
		res = Operations.getType(name)
	if not res:
		raise Exception("No model type for Python class: %s" % (aclass))
	else:
		return res

# EOF
