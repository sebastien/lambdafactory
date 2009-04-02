# BUT: Writer outputs properties:{ a:{}, b:new Object() } while properties
# should be defined in the constructor
@class F
	@property a = {}
	@property b = new Object ()
@end
