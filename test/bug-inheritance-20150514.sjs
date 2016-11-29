# EXPECTS:<<<
# HANDLERS A
# HANDLERS A
# HANDLERS A
# <<<
@class A
	@shared HANDLERS_KEY = "A"
	@method trigger
		console log ("HANDLERS", HANDLERS_KEY)
	@end
@end

@class B: A

	@method trigger
		console log ("HANDLERS", HANDLERS_KEY)
	@end

@end

@class C: B

	@method trigger
		console log ("HANDLERS", HANDLERS_KEY)
	@end

@end

new A () trigger ()
new B () trigger ()
new C () trigger ()
