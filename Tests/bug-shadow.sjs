@module state

@class A

	@property state

	@constructor state:State
		self state = state
	@end

@end

@class B: A

	@constructor state:State
		super (state)
	@end

	@method state state
		print ("STATE", state)
	@end

@end


