# BUG: 'map a' is transleted to 'extend.map.a = 2;' (JS backend)
# while it works when removing the 'ready' prefix
# var a = {
ready {
	var map = {a:1}
	map a = 2
}
