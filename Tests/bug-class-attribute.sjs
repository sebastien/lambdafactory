@class A
	@property uis = {}
	@constructor
		self uis = {a:1}
	@end
@end

@class B:A
	@property uis = {}
@end

var b = new B ()
# Prints ({}) while it should be ({a:1})
print (b uis)
