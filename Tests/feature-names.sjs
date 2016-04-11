@class A


	@shared   s = [__name__, __scope__]
	@property p = [__name__, __scope__]

	@method f
		console log (__name__, __scope__)
	@end

@end

@function g
	console log (__name__, __scope__)
@end

console log (__name__, __scope__)
