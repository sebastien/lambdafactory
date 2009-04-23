// 8< ---[extend/__module__.as]---
package extend {
	public class __module__ {
	import flash.utils.getQualifiedSuperclassName
	import flash.utils.getDefinitionByName
	public static var Counters={'Instances':0}
	public static var ErrorCallback=undefined
	public static var PrintCallback=undefined
	public static var Registry={}
		/** Classes are created using extend by giving a dictionary that contains the
		following keys:
		
		- 'name', an optional name for this class
		- 'parent', with a reference to a parent class (created with extend)
		- 'initialize', with a function to be used as a constructor
		- 'properties', with a dictionary of instance attributes
		- 'methods', with a dictionary of instance methods
		- 'shared', with a dictionary of class attributes
		- 'operations', with a dictionary of class operations
		
		Invoking the 'Class' function will return you a _Class Object_ that
		implements the following API:
		
		- 'isClass()' returns *true*( (because this is an object, not a class)
		- 'getName()' returns the class name, as a string
		- 'getParent()' returns a reference to the parent class
		- 'getOperation(n)' returns the operation with the given name
		- 'hasInstance(o)' tells if the given object is an instance of this class
		- 'isSubclassOf(c)' tells if the given class is a subclass of this class
		- 'listMethods()' returns a dictionary of *methods* available for this class
		- 'listOperations()' returns a dictionary of *operations* (class methods)
		- 'listShared()' returns a dictionary of *class attributes*
		- 'listProperties()' returns a dictionary of *instance attributes*
		- 'bindMethod(o,n)' binds the method with the given name to the given object
		- 'proxyWithState(o)' returns a *proxy* that will use the given object as if
		it was an instance of this class (useful for implementing 'super')
		
		When you instanciate your class, objects will have the following methods
		available:
		
		- 'isClass()' returns *true*( (because this is an object, not a class)
		- 'getClass()' returns the class of this instance
		- 'getMethod(n)' returns the bound method which name is 'n'
		- 'getCallback(n)' the equivalent of 'getMethod', but will give the 'this' as
		additional last arguments (useful when you the invoker changes the 'this',
		which happens in event handlers)
		- 'isInstance(c)' tells if this object is an instance of the given class
		
		Using the 'Class' function is very easy (in *Sugar*):
		
		>   var MyClass = extend Class {
		>      name:"MyClass"
		>      initialize:{
		>         self message = "Hello, world !"
		>      }
		>      methods:{
		>        helloWorld:{print (message)}
		>      }
		>   }
		
		instanciating the class is very easy too
		
		>   var my_instance = new MyClass()
		*/
		public static function Class (declaration){
			var full_name=declaration.name;
			var class_object=function( ... arguments){
				if ( (! ((arguments.length == 1) && (arguments[0] == '__Extend_SubClass__'))) )
				{
					 var properties = class_object.listProperties()
					 for ( var prop in properties ) {
					   this[prop] = properties[prop];
					 }
					
					if ( target.initialize )
					{
						return target.initialize.apply(target, arguments)
					}
				}
			};
			class_object.isClass = function( ... arguments){
				return true
			};
			class_object._parent = declaration.parent;
			class_object._name = declaration.name;
			class_object._properties = {'all':{}, 'inherited':{}, 'own':{}};
			class_object._shared = {'all':{}, 'inherited':{}, 'own':{}};
			class_object._operations = {'all':{}, 'inherited':{}, 'own':{}, 'fullname':{}};
			class_object._methods = {'all':{}, 'inherited':{}, 'own':{}, 'fullname':{}};
			class_object.getName = function( ... arguments){
				return class_object._name
			};
			class_object.getParent = function( ... arguments){
				return class_object._parent
			};
			class_object.isSubclassOf = function(c, ... arguments){
				var parent=this;
				while (parent)
				{
					if ( (parent == c) )
					{
						return True
					}
					parent = parent.getParent();
				}
				return False
			};
			class_object.hasInstance = function(o, ... arguments){
				return o.getClass().isSubclassOf(class_object)
			};
			class_object.bindMethod = function(object, methodName, ... arguments){
				var this_method=object[methodName];
				return function( ... arguments){
					var a=arguments;
					if ( (a.length == 0) )
					{
						return this_method.call(object)
					}
					else if ( (a.length == 1) )
					{
						return this_method.call(object, a[0])
					}
					else if ( (a.length == 2) )
					{
						return this_method.call(object, a[0], a[1])
					}
					else if ( (a.length == 3) )
					{
						return this_method.call(object, a[0], a[1], a[2])
					}
					else if ( (a.length == 4) )
					{
						return this_method.call(object, a[0], a[1], a[2], a[3])
					}
					else if ( (a.length == 5) )
					{
						return this_method.call(object, a[0], a[1], a[2], a[3], a[4])
					}
					else if ( True )
					{
						var args=[];
						args.concat(arguments)
						return this_method.apply(object, args)
					}
				}
			};
			class_object.bindCallback = function(object, methodName, ... arguments){
				var this_method=object[methodName];
				return function( ... arguments){
					var a=arguments;
					if ( (a.length == 0) )
					{
						return this_method.call(object, target)
					}
					else if ( (a.length == 1) )
					{
						return this_method.call(object, a[0], target)
					}
					else if ( (a.length == 2) )
					{
						return this_method.call(object, a[0], a[1], target)
					}
					else if ( (a.length == 3) )
					{
						return this_method.call(object, a[0], a[1], a[2], target)
					}
					else if ( (a.length == 4) )
					{
						return this_method.call(object, a[0], a[1], a[2], a[3], target)
					}
					else if ( (a.length == 5) )
					{
						return this_method.call(object, a[0], a[1], a[2], a[3], a[4], target)
					}
					else if ( True )
					{
						var args=[];
						args.concat(arguments)
						args.push(target)
						return this_method.apply(object, args)
					}
				}
			};
			class_object.getOperation = function(name, ... arguments){
				var this_operation=class_object[name];
				return function( ... arguments){
					return this_operation.apply(class_object, arguments)
				}
			};
			class_object.listMethods = function(o, i, ... arguments){
				if ( (o === Undefined) )
				{
					o = True;
				}
				if ( (i === Undefined) )
				{
					i = True;
				}
				if ( (o && i) )
				{
					return class_object._methods.all
				}
				else if ( ((! o) && i) )
				{
					return class_object._methods.inherited
				}
				else if ( (o && (! i)) )
				{
					return class_object._methods.own
				}
				else if ( True )
				{
					return {}
				}
			};
			class_object.listOperations = function(o, i, ... arguments){
				if ( (o === Undefined) )
				{
					o = True;
				}
				if ( (i === Undefined) )
				{
					i = True;
				}
				if ( (o && i) )
				{
					return class_object._operations.all
				}
				else if ( ((! o) && i) )
				{
					return class_object._operations.inherited
				}
				else if ( (o && (! i)) )
				{
					return class_object._operations.own
				}
				else if ( True )
				{
					return {}
				}
			};
			class_object.listShared = function(o, i, ... arguments){
				if ( (o === Undefined) )
				{
					o = True;
				}
				if ( (i === Undefined) )
				{
					i = True;
				}
				if ( (o && i) )
				{
					return class_object._shared.all
				}
				else if ( ((! o) && i) )
				{
					return class_object._shared.inherited
				}
				else if ( (o && (! i)) )
				{
					return class_object._shared.own
				}
				else if ( True )
				{
					return {}
				}
			};
			class_object.listProperties = function(o, i, ... arguments){
				if ( (o === Undefined) )
				{
					o = True;
				}
				if ( (i === Undefined) )
				{
					i = True;
				}
				if ( (o && i) )
				{
					return class_object._properties.all
				}
				else if ( ((! o) && i) )
				{
					return class_object._properties.inherited
				}
				else if ( (o && (! i)) )
				{
					return class_object._properties.own
				}
				else if ( True )
				{
					return {}
				}
			};
			class_object.proxyWithState = function(o, ... arguments){
				var proxy={};
				var constr=Undefined;
				var wrapper=function(f, ... arguments){
					return function( ... arguments){
						return f.apply(o, arguments)
					}
				};
				var proxy_object=function( ... arguments){
					return class_object.prototype.initialize.apply(o, arguments)
				};
				proxy_object.prototype = proxy;
				 for (var key in class_object.prototype) {
				  var w = wrapper(class_object.prototype[key])
				  if (key == "initialize") { constr=w }
				  proxy[key] = w
				  // This should not be necessary
				  proxy_object[key] = w
				 }
				
				proxy_object.getSuper = function( ... arguments){
					return class_object.getParent().proxyWithState(o)
				};
				return proxy_object
			};
			if ( declaration.parent != undefined ) {
				// We proxy parent operations
				for ( var name in declaration.parent._operations.fullname ) {
					var operation = declaration.parent._operations.fullname[name]
					class_object._operations.fullname[name] = operation
					class_object[name] = operation
				}
				for ( var name in declaration.parent._operations.all ) {
					var operation = declaration.parent[name]
					class_object[name] = operation
					class_object._operations.all[name] = operation
					class_object._operations.inherited[name] = operation
				}
				for ( var name in declaration.parent._methods.all ) {
					var method = declaration.parent._methods.all[name]
					class_object._methods.all[name] = method
					class_object._methods.inherited[name] = method
				}
				// We copy parent class attributes default values
				for ( var name in declaration.parent._shared.all ) {
					var attribute = declaration.parent._shared.all[name]
					class_object[name] = attribute
					class_object._shared.all[name] = attribute
					class_object._shared.inherited[name] = attribute
				}
				// We copy parent instance attributes default values
				for ( var name in declaration.parent._properties.all ) {
					var prop = declaration.parent._properties.all[name]
					class_object._properties.all[name] = prop
					class_object._properties.inherited[name] = prop
				}
			}
			if ( declaration.operations != undefined ) {
				for ( var name in declaration.operations ) {
					var operation = declaration.operations[name]
					class_object[name] = operation
					class_object[full_name + "_" + name] = operation
					class_object._operations.all[name] = operation
					class_object._operations.all[name] = operation
					class_object._operations.own[name] = operation
					class_object._operations.fullname[full_name + "_" + name] = operation
				}
			}
			if ( declaration.methods != undefined ) {
				for ( var name in declaration.methods ) {
					var method = declaration.methods[name]
					class_object._methods.all[name] = method
					class_object._methods.own[name] = method
				}
			}
			if ( declaration.shared != undefined ) {
				for ( var name in declaration.shared ) {
					var attribute = declaration.shared[name]
					class_object[name] = attribute
					class_object._shared.all[name] = attribute
					class_object._shared.own[name] = attribute
				}
			}
			if ( declaration.properties != undefined ) {
				for ( var name in declaration.properties ) {
					var attribute = declaration.properties[name]
					class_object._properties.all[name] = attribute
					class_object._properties.own[name] = attribute
				}
			}
			
			var instance_proto={};
			if ( declaration.parent )
			{
				instance_proto = new declaration.parent('__Extend_SubClass__');
				instance_proto.constructor = class_object;
			}
			instance_proto.isInstance = Undefined;
			instance_proto.getClass = function( ... arguments){
				return class_object
			};
			instance_proto.isClass = function( ... arguments){
				return False
			};
			instance_proto.getMethod = function(methodName, ... arguments){
				var this_object=target;
				return class_object.bindMethod(this_object, methodName)
			};
			instance_proto.getCallback = function(methodName, ... arguments){
				var this_object=target;
				return class_object.bindCallback(this_object, methodName)
			};
			instance_proto.isInstance = function(c, ... arguments){
				return c.hasInstance(target)
			};
			if ( declaration.initialize )
			{
				instance_proto.initialize = declaration.initialize;
			}
			else if ( True )
			{
				instance_proto.instance_proto = {};
			}
			instance_proto.getSuper = function(c, ... arguments){
				return c.proxyWithState(target)
			};
			if ( declaration.operations != undefined ) {
				for ( var name in declaration.operations ) {
					instance_proto[name] = instance_proto[full_name + "_" + name] = class_object.getOperation(name)
			}}
			if ( declaration.methods != undefined ) {
				for ( var name in declaration.methods ) {
					instance_proto[name] = instance_proto[full_name + "_" + name] = declaration.methods[name]
			}}
			if ( declaration.initialize != undefined ) {
				instance_proto.initialize = instance_proto[full_name + "_initialize"] = declaration.initialize
			}
			
			class_object.prototype = instance_proto;
			if ( declaration.name )
			{
				if ( (extend.Registry != Undefined) )
				{
					extend.Registry[declaration.name] = class_object;
				}
			}
			return class_object
		}
		public static function Protocol (pdata){
		}
		public static function Singleton (sdata){
		}
		/** The 'invoke' method allows advanced invocation (supporting by name, as list
		and as map invocation schemes) provided the given function 'f' has proper
		'__meta__' annotation.
		
		These annotations are expected to be like:
		
		>    f __meta__ = {
		>        arity:2
		>        arguments:{
		>           b:2,
		>           "*":[1]
		>           "**":{c:3,d:4}
		>        }
		>    }
		
		*/
		public static function invoke (t, f, args, extra){
			var meta=f['__meta__'];
			var actual_args=[];
			extend.__module__.iterate(extra['*'], function(v, ... arguments){
				args.push(v)
			}, __this__)
			extend.__module__.iterate(extra['**'], function(v, k, ... arguments){
				extra[k] = v;
			}, __this__)
			extend.__module__.iterate(args, function(v, ... arguments){
				actual_args.push(args)
			}, __this__)
			var start=args.length;
			while ((start < meta.arity))
			{
				var arg=meta.arguments[start];
				actual_args.push(extra[arg.name])
				start = (start + 1);
			}
			return f.apply(t, actual_args)
		}
		/** Creates a new list composed of elements in the given range, determined by
		the 'start' index and the 'end' index. This function will automatically
		find the proper step (wether '+1' or '-1') depending on the bounds you
		specify.
		*/
		public static function range (start:Number, end:Number, step:Number){
			var result=[];
			 if (start < end ) {
			   for ( var i=start ; i<end ; i++ ) {
			     result.push(i);
			   }
			 }
			 else if (start > end ) {
			   for ( var i=start ; i>end ; i-- ) {
			     result.push(i);
			   }
			 }
			
			return result
		}
		/** Iterates on the given values. If 'value' is an array, the _callback_ will be
		invoked on each item (giving the 'value[i], i' as argument) until the callback
		returns 'false'. If 'value' is a dictionary, the callback will be applied
		on the values (giving 'value[k], k' as argument). Otherwise the object is
		expected to define both 'length' or 'getLength' and 'get' or 'getItem' to
		enable the iteration.
		*/
		public static function iterate (value, callback:Function, context:Object){
			  if ( !value ) { return }
			  if ( value.length != undefined ) {
			    var length = undefined
			    // Is it an object with the length() and get() protocol ?
			    if ( typeof(value.length) == "function" ) {
			      length = value.length()
			      for ( var i=0 ; i<length ; i++ ) {
			        var cont = callback.call(context, value.get(i), i)
			        if ( cont == false ) { i = length + 1 };
			      }
			    // Or a plain array ?
			    } else {
			      length = value.length
			      for ( var i=0 ; i<length ; i++ ) {
			       var cont = callback.call(context, value[i], i);
			       if ( cont == false ) { i = length + 1 };
			      }
			    }
			  } else {
			    for ( var k in value ) {
			      var cont = callback.call(context, value[k], k);
			      if ( cont == false ) { i = length + 1 };
			    }
			  }
			
		}
		/** This is a utility function that will return the rest of the given
		arguments list, without using the 'slice' operation which is only
		available to arrays.
		*/
		public static function sliceArguments (args, index){
			var res=[];
			 while (index<args.length) { res.push(args[index++]) }
			
			return res
		}
		public static function slice (value, start=0, end=undefined){
			end = end === undefined ? Undefined : end
			if ( extend.isString(value) )
			{
				if ( (end === Undefined) )
				{
					end = value.length;
				}
				if ( (start < 0) )
				{start = (value.length + start);}
				if ( (end < 0) )
				{end = (value.length + end);}
				return value.substring(start, end)
			}
			else if ( extend.isList(value) )
			{
				if ( (end === Undefined) )
				{
					end = value.length;
				}
				if ( (start < 0) )
				{start = (value.length + start);}
				if ( (end < 0) )
				{end = (value.length + end);}
				return value.slice(start, end)
			}
			else if ( True )
			{
				throw ('Unsupported type for slice:' + value)
			}
		}
		public static function len (value){
			if ( extend.isList(value) )
			{
				return value.length
			}
			else if ( extend.isObject(value) )
			{
				if ( value.length )
				{
					return value.length
				}
				else if ( value.__len__ )
				{
					return value.__len__()
				}
			}
			else if ( True )
			{
				return None
			}
		}
		public static function type (value){
			return typeof(value)
		}
		public static function access (value, index){
			if ( extend.isList(value) )
			{
				if ( (index >= 0) )
				{
					return value[index]
					
				}
				else if ( True )
				{
					return value[value.length + index]
					
				}
			}
			else if ( True )
			{
				return value[index]
				
			}
		}
		/** Returns true if the given value is in the given list
		*/
		public static function isIn (value, list){
			if ( extend.isList(list) )
			{
				 for ( var i=0 ; i<list.length ; i++) {
				   if (list[i]==value) { return true }
				 }
				 return false
				
			}
			else if ( extend.isMap(list) )
			{
				 for ( var i in list ) {
				   if (list[i]==value) { return true }
				 }
				 return false
				
			}
			else if ( True )
			{
				return False
			}
		}
		public static function createMapFromItems (items){
			items = extend.__module__.sliceArguments(arguments,0)
			 var result = {}
			 for ( var i=0 ; i<items.length ; i++ ) {
			   result[items[i][0]] = items[i][1]
			 }
			 return result
			
		}
		public static function isDefined (value){
			return (! (value === Undefined))
		}
		public static function isList (value){
			 return Object.prototype.toString.call(value) === '[object Array]';
			
		}
		public static function isNumber (value){
			return (typeof(value) == 'number')
		}
		public static function isString (value){
			return (typeof(value) == 'string')
		}
		public static function isMap (value){
			 return !!(!(value===null) && typeof value == "object" && !extend.isList(value))
			
		}
		public static function isFunction (value){
			 return !!(typeof value == "function")
			
		}
		public static function isObject (value){
			 return !!(typeof value == "object")
			
		}
		/** Tells if the given value is an instance (in the sense of extend) of the
		given 'ofClass'. If there is no given class, then it will just return
		true if the value is an instance of any class.
		*/
		public static function isInstance (value, ofClass=undefined){
			ofClass = ofClass === undefined ? Undefined : ofClass
			if ( ofClass )
			{
				return (extend.isDefined(value.getClass) && value.isInstance(ofClass))
			}
			else if ( True )
			{
				return extend.isDefined(value.getClass)
			}
		}
		public static function getMethodOf (instance, name){
			return instance[name]
		}
		public static function getClassOf (instance){
			return getDefinitionByName(getQualifiedSuperclassName(instance));
			
			return instance.getClass()
			
		}
		/** Prints the given arguments to the JavaScript console (available in Safari
		and in Mozilla if you've installed FireBug), or using the 'print' command
		in SpiderMonkey. If neither 'console' or 'print' is defined,
		this won't do anything.
		
		When objects are given as arguments, they will be printed using the
		'toSource' method they offer.
		
		Example:
		
		>    extend print ("Here is a dict:", {a:1,b:2,c:3})
		
		will output
		
		>    "Here is a dict: {a:1,b:2,c:3}"
		*/
		public static function print (args){
			args = extend.__module__.sliceArguments(arguments,0)
			var pr_func=eval('print');
			if ( (((typeof(console) == 'undefined') && (typeof(pr_func) === 'undefined')) && (extend.PrintCallback === Undefined)) )
			{
				return None
			}
			var res='';
			 for ( var i=0 ; i<args.length ; i++ ) {
			   var val = args[i]
			   if ( val!=undefined && typeof(val) == "object" && val.toSource != undefined) { val = val.toSource() }
			   if ( i<args.length-1 ) { res += val + " " }
			   else { res += val }
			 }
			
			if ( (extend.PrintCallback === Undefined) )
			{
				if ( (typeof(console) != 'undefined') )
				{
					console.log(res)
				}
				else if ( ((typeof(document) == 'undefined') && (typeof(pr_func) != 'undefined')) )
				{
					pr_func(res)
				}
			}
			else if ( True )
			{
				extend.PrintCallback(res)
			}
		}
		public static function error (message){
			if ( extend.ErrorCallback )
			{
				extend.ErrorCallback(message)
			}
			else if ( True )
			{
				extend.print(('[!] ' + message))
			}
		}
		public static function assert (predicate, message){
			if ( (! predicate) )
			{
				extend.error(message)
			}
		}
		public static function getClass (name){
			return extend.Registry[name]
		}
		public static function getParentClass (object){
			return extend.Registry[name]
		}
		public static function getClasses (){
			return extend.Registry
		}
		public static function getMethod (name, object){
		}
		public static function getSuperMethod (name, object){
		}
		public static function getChildrenOf (aClass){
			var res={};
			var values = extend.getClasses()
			for ( key in values ) {
				if ( values[key] != aClass && values[key].isSubclassOf(aClass) )
				{ res[key] = values[key] }
			}
			
			return res
		}
		public static function car (list){
		}
		public static function cdr (list){
		}
		public static function cons (list){
		}
		public static function map (callback, iterable){
			var result=[];
			extend.__module__.iterate(iterable, function(e, ... arguments){
				result.append(callback(e))
			}, __this__)
			return result
		}
		public static function filter (callback, iterable){
			var result=[];
			extend.__module__.iterate(iterable, function(e, ... arguments){
				if ( callback(e) )
				{
					result.append(e)
				}
			}, __this__)
			return result
		}
		public static function reduce (callback, iterable){
			var first=True;
			var result=Undefined;
			extend.__module__.iterate(iterable, function(e, ... arguments){
				if ( first )
				{
					result = callback(e);
					first = False;
				}
				else if ( True )
				{
					result = callback(e, result);
				}
			}, __this__)
			return result
		}
		public static function extendPrimitiveTypes (){
			String.prototype.__len__ = function( ... arguments){
				return target.length
			};
			Array.prototype.extend = function(array, ... arguments){
				extend.__module__.iterate(array, function(e, ... arguments){
					target.append(e)
				}, __this__)
			};
			Array.prototype.append = function(e, ... arguments){
				target.push(e)
			};
			Array.prototype.insert = function(e, i, ... arguments){
				target.splice(i, e)
			};
			Array.prototype.slice = function( ... arguments){
			};
			Array.prototype.__iter__ = function( ... arguments){
				return target.length
			};
			Array.prototype.__len__ = function( ... arguments){
				return target.length
			};
			Object.prototype.keys = function( ... arguments){
				var result=[];
				for (var k in this) { var key=k ; result.push(key) }
				
				return result
			};
			Object.prototype.items = function( ... arguments){
				var result=[];
				for (var k in this) { var key=k ; result.push([key,this[key]]) }
				
				return result
			};
			Object.prototype.values = function( ... arguments){
				var result=[];
				for (var k in this) { var key=k ; result.push([key,this[key]]) }
				
				return result
			};
			Object.prototype.hasKey = function(key, ... arguments){
				return (typeof(this[key]) != 'undefined')
			};
			Object.prototype.get = function(key, ... arguments){
				return target[key]
			};
			Object.prototype.set = function(key, value, ... arguments){
				target[key] = value;
				return this
			};
			Object.prototype.setDefault = function(key, value, ... arguments){
				if ( (typeof(target[key]) != 'undefined') )
				{
					return target[key]
				}
				else if ( True )
				{
					target[key] = value;
					return value
				}
			};
			Object.prototype.__iter__ = function( ... arguments){
			};
			Object.prototype.__len__ = function( ... arguments){
				return target.keys().length
			};
		}
	}
}
