# EXPECTED: The fact that A is defined after PROPERTY should not cause a
# failure. PROPERTY value evaluation should happen before module initialization,
# but after module declaration.
@shared PROPERTY = new A()
@class A
	@constructor
	@end
@end
# EOF
