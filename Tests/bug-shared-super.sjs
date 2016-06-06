@class A
	@shared V = {A:"A"}
@end

@class B: A
	@shared V = merge ({B:"B"}, super V)
@end

console log (B V)
