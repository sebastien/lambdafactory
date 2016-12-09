# Tests that class parents are properly referenced in the local module.
# Additionally checks that shadowing the current module works with
# constructors/parent resolution.
@module a
@class A
@end
@class B:A
	@constructor a=10
		# The a=10 will shadow the module name, so we also make sure this works
		super()
	@end
@end
