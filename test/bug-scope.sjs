@class A

	@property env

@end

@class B: A

	@method render env=Undefined, data=Undefined, view=Undefined
		env style {fill:"#F0F0F0"}
		env rect (w,h)
	@end

@end


