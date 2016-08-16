@module state

@class A

	@shared IDS = 0
	@property state

	@constructor state:State
		self state = state
		A IDS += 1
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


