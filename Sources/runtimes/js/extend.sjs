@module Extend
| This module implements a complete OOP layer for JavaScript that makes it
| easy to develop highly structured JavaScript applications.
|
| Extend 2.0 is a rewritten, simplified version of the Extend 1 library. It is
| not compatible with the previous versions, but the API will be stable from
| this release.

# TODO: Add a class registry (needs @shared on Modules)

@function create attributes, methods, operations, parent, name

	# FIXME: Rename this to target
	# var new_class = { this initialize apply (this, arguments) }
	var new_class = {}
	var new_class_proto = {methods:{},operations:{}}

	# We setup the new class properties
	new_class getClass             = { return new_class_proto }
	new_class_proto name           = name
	new_class_proto parent         = parent
	new_class_proto getName        = {return new_class_proto name}
	new_class_proto getParent      = {return new_class_proto parent}
	new_class_proto getMethod      = {name|return new_class_proto[name]}
	new_class_proto getClassMethod = {name|return new_class_proto[name]}
	new_class_proto getConstructor = {return new_class_proto initialize}

	# We register methods and operations in the prototype
	@embed JavaScript
		for ( var name in methods )    { new_class[name] = methods[name]; };
		for ( var name in attributes ) { new_class[name] = attributes[name]; };
		for ( var name in operations ) { new_class[name] = operations[name]; };
	@end

	# We assign the proto to the current class
	new_class prototype = new_class_proto
	return new_class

@end

@function protocol data
@end

@function singleton data
@end

# EOF vim: syn=sugar sw=4 ts=4 noet
