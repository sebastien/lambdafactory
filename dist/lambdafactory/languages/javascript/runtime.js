// 8< ---[extend.js]---

var extend=(typeof('extend')!='undefined' && extend && extend.module && extend.module("extend")) || extend || {};
(function(extend){
var self=__module__=extend
extend.__VERSION__='3.0.0';
extend.modules={"_expected":0, "_ready":[]}
extend.Counters={"Instances":0, "Classes":0}
extend.module=	function(name){
		var self=extend;
		if ( (! extend.isDefined(extend.modules[name])) )
		{
			extend.modules[name] = {"__name__":name};
		}
		return extend.modules[name];
	}
extend._wrapMethod=	function(o, n){
		var self=extend;
		return function(){
			var m = o[n];
			return m.apply(o,arguments);
			
		};
	}
extend.Class=	function(declaration){
		// Classes are created using extend by giving a dictionary that contains the
		// following keys:
		// 
		// - 'name', an optional name for this class
		// - 'parent', with a reference to a parent class (created with extend)
		// - 'initialize', with a function to be used as a constructor
		// - 'properties', with a dictionary of instance attributes
		// - 'methods', with a dictionary of instance methods
		// - 'shared', with a dictionary of class attributes
		// - 'operations', with a dictionary of class operations
		// 
		// Invoking the 'Class' function will return you a _Class Object_ that
		// implements the following API:
		// 
		// - 'isClass()' returns *true*( (because this is an object, not a class)
		// - 'getName()' returns the class name, as a string
		// - 'getParent()' returns a reference to the parent class
		// - 'getOperation(n)' returns the operation with the given name
		// - 'hasInstance(o)' tells if the given object is an instance of this class
		// - 'isSubclassOf(c)' tells if the given class is a subclass of this class
		// - 'listMethods()' returns a dictionary of *methods* available for this class
		// - 'listOperations()' returns a dictionary of *operations* (class methods)
		// - 'listShared()' returns a dictionary of *class attributes*
		// - 'listProperties()' returns a dictionary of *instance attributes*
		// - 'proxyWithState(o)' returns a *proxy* that will use the given object as if
		// it was an instance of this class (useful for implementing 'super')
		// 
		// When you instanciate your class, objects will have the following methods
		// available:
		// 
		// - 'isClass()' returns *false*( (because this is an object, not a class)
		// - 'getClass()' returns the class of this instance
		// - 'getMethod(n)' returns the bound method which name is 'n'
		// - 'getCallback(n)' the equivalent of 'getMethod', but will give the 'this' as
		// additional last arguments (useful when you the invoker changes the 'this',
		// which happens in event handlers)
		// - 'isInstance(c)' tells if this object is an instance of the given class
		// 
		// Using the 'Class' function is very easy (in *Sugar*):
		// 
		// >   var MyClass = extend Class {
		// >      name:"MyClass"
		// >      initialize:{
		// >         self message = "Hello, world !"
		// >      }
		// >      methods:{
		// >        helloWorld:{print (message)}
		// >      }
		// >   }
		// 
		// instanciating the class is very easy too
		// 
		// >   var my_instance = new MyClass()
		var self=extend;
		var full_name=declaration.name;
		var class_object=function(){
			if ( (! ((arguments.length == 1) && (arguments[0] == "__Extend_SubClass__"))) )
			{
				 var properties = class_object.listProperties()
				 for ( var prop in properties ) {
				   this[prop] = properties[prop];
				 }
				
				if ( this.initialize )
				{
					return this.initialize.apply(this, arguments);
				}
			}
		};
		class_object.isClass = function(){
			return true;
		};
		class_object._parent = declaration.parent;
		class_object._name = declaration.name;
		class_object._properties = {"all":{}, "inherited":{}, "own":{}};
		class_object._shared = {"all":{}, "inherited":{}, "own":{}};
		class_object._operations = {"all":{}, "inherited":{}, "own":{}, "fullname":{}};
		class_object._methods = {"all":{}, "inherited":{}, "own":{}, "fullname":{}};
		class_object.getName = function(){
			return class_object._name;
		};
		class_object.getParent = function(){
			return class_object._parent;
		};
		class_object.id = extend.Counters.Classes;
		class_object._wrapMethod = extend._wrapMethod;
		extend.Counters.Classes = (extend.Counters.Classes + 1);
		class_object.isSubclassOf = function(c){
			var parent=this;
			while (parent) 
			{
				if ( (parent == c) )
				{
					return true;
				}
				parent = parent.getParent();
			}
			return false;
		};
		class_object.hasInstance = function(o){
			return ((o && extend.isDefined(o.getClass)) && o.getClass().isSubclassOf(class_object));
		};
		class_object.getOperation = function(name){
			var this_operation=class_object[name];
			if ( (! this_operation) )
			{
				return null;
			}
			if ( (! class_object.__operationCache) )
			{
				class_object.__operationCache = {};
			}
			var o=class_object.__operationCache[name];
			if ( (! o) )
			{
				o = function(){
					return this_operation.apply(class_object, arguments);
				};
				class_object.__operationCache[name] = o;
			}
			return o;
		};
		class_object.listMethods = function(o, i){
			if ( (o === undefined) )
			{
				o = true;
			}
			if ( (i === undefined) )
			{
				i = true;
			}
			if ( (o && i) )
			{
				return class_object._methods.all;
			}
			else if ( ((! o) && i) )
			{
				return class_object._methods.inherited;
			}
			else if ( (o && (! i)) )
			{
				return class_object._methods.own;
			}
			else
			{
				return {};
			}
		};
		class_object.listOperations = function(o, i){
			if ( (o === undefined) )
			{
				o = true;
			}
			if ( (i === undefined) )
			{
				i = true;
			}
			if ( (o && i) )
			{
				return class_object._operations.all;
			}
			else if ( ((! o) && i) )
			{
				return class_object._operations.inherited;
			}
			else if ( (o && (! i)) )
			{
				return class_object._operations.own;
			}
			else
			{
				return {};
			}
		};
		class_object.listShared = function(o, i){
			if ( (o === undefined) )
			{
				o = true;
			}
			if ( (i === undefined) )
			{
				i = true;
			}
			if ( (o && i) )
			{
				return class_object._shared.all;
			}
			else if ( ((! o) && i) )
			{
				return class_object._shared.inherited;
			}
			else if ( (o && (! i)) )
			{
				return class_object._shared.own;
			}
			else
			{
				return {};
			}
		};
		class_object.listProperties = function(o, i){
			if ( (o === undefined) )
			{
				o = true;
			}
			if ( (i === undefined) )
			{
				i = true;
			}
			if ( (o && i) )
			{
				return class_object._properties.all;
			}
			else if ( ((! o) && i) )
			{
				return class_object._properties.inherited;
			}
			else if ( (o && (! i)) )
			{
				return class_object._properties.own;
			}
			else
			{
				return {};
			}
		};
		class_object.proxyWithState = function(o){
			var proxy={};
			var constr=undefined;
			var wrapper=function(f){
				return function(){
					return f.apply(o, arguments);
				};
			};
			var proxy_object=function(){
				return class_object.prototype.initialize.apply(o, arguments);
			};
			proxy_object.prototype = proxy;
			 for (var key in class_object.prototype) {
			  var w = wrapper(class_object.prototype[key])
			  if (key == "initialize") { constr=w }
			  proxy[key] = w
			  // This should not be necessary, but it actually is! -- should investigae at some point
			  proxy_object[key] = w
			 }
			
			proxy_object.getSuper = function(){
				return class_object.getParent().proxyWithState(o);
			};
			return proxy_object;
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
			instance_proto = new declaration.parent("__Extend_SubClass__");
			instance_proto.constructor = class_object;
		}
		instance_proto.isInstance = undefined;
		instance_proto.getClass = function(){
			return class_object;
		};
		instance_proto.isClass = function(){
			return false;
		};
		instance_proto._methodCache = undefined;
		instance_proto.getMethod = function(methodName){
			var this_object=this;
			if ( (! this_object.__methodCache) )
			{
				this_object.__methodCache = {};
			}
			var m=this_object.__methodCache[methodName];
			if ( (! m) )
			{
				m = class_object._wrapMethod(this_object, methodName);
				this_object.__methodCache[methodName] = m;
			}
			return m;
		};
		instance_proto.getCallback = function(methodName){
			var this_object=this;
			if ( (! this_object.__methodCache) )
			{
				this_object.__methodCache = {};
			}
			var callback_name=(methodName + "_k");
			var m=this_object.__methodCache[methodName];
			if ( m )
			{
				m
			}
			else
			{
				m = class_object._wrapMethod(this_object, methodName);
				this_object.__methodCache[callback_name] = m;
				return m;
			}
		};
		instance_proto.isInstance = function(c){
			return c.hasInstance(this);
		};
		if ( declaration.initialize )
		{
			instance_proto.initialize = declaration.initialize;
		}
		else
		{
			instance_proto.instance_proto = {};
		}
		instance_proto.getSuper = function(c){
			if ( (typeof(this._extendProxyWithState) == "undefined") )
			{
				this._extendProxyWithState = extend.createMapFromItems([c.id,c.proxyWithState(this)]);
			}
			else if ( (typeof(this._extendProxyWithState[c.id]) == "undefined") )
			{
				this._extendProxyWithState[c.id] = c.proxyWithState(this);
			}
			return this._extendProxyWithState[c.id];
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
			if ( (extend.Registry != undefined) )
			{
				extend.Registry[declaration.name] = class_object;
			}
		}
		return class_object;
	}
extend.Protocol=	function(pdata){
		var self=extend;
	}
extend.Singleton=	function(sdata){
		var self=extend;
	}
extend.ExceptionCallback=undefined
extend.ErrorCallback=undefined
extend.WarningCallback=undefined
extend.DebugCallback=undefined
extend.PrintCallback=undefined
extend.FLOW_BREAK=1
extend.FLOW_CONTINUE=2
extend.FLOW_RETURN=3
extend.Nothing=new Object()
extend.Timeout=new Object()
extend.Error=new Object()
extend.Type={"Undefined":"undefined", "None":"none", "Number":"number", "String":"string", "List":"list", "Map":"map", "Object":"object", "Function":"function", "Instance":"instance", "Unknown":"unknown"}
extend.OPTIONS={"modulePrefix":"lib/sjs/", "moduleSuffix":".sjs"}
extend.require=	function(module, callback){
		var self=extend;
		if ( (! extend.modules[module]) )
		{
			extend.modules[module] = extend.Nothing;
			var head=document.getElementByTagName("head")[0];
			var script=document.createElement("script");
			script.setAttribute("src", ((extend.OPTIONS.modulePrefix + module) + extend.OPTIONS.moduleSuffix));
			head.appendChild(script);
		}
		else
		{
			return extend.modules[module];
		}
	}
extend.invoke=	function(t, f, args, extra){
		// The 'invoke' method allows advanced invocation (supporting by name, as list
		// and as map invocation schemes) provided the given function 'f' has proper
		// '__meta__' annotation.
		// 
		// These annotations are expected to be like:
		// 
		// >    f __meta__ = {
		// >        arity:2
		// >        arguments:{
		// >           b:2,
		// >           "*":[1]
		// >           "**":{c:3,d:4}
		// >        }
		// >    }
		// 
		var self=extend;
		var meta=f["__meta__"];
		var actual_args=[];
		var __b=extra["*"];var __c=__b instanceof Array ? __b : Object.getOwnPropertyNames(__b||{});var __e=__c.length;for (var __d=0;__d<__e;__d++){var __a=(__c===__b)?__d:__c[__d];var v=__b[__a];	args.push(v)}
		var __f=extra["**"];var __g=__f instanceof Array ? __f : Object.getOwnPropertyNames(__f||{});var __i=__g.length;for (var __h=0;__h<__i;__h++){var k=(__g===__f)?__h:__g[__h];var v=__f[k];	extra[k] = v}
		var __k=args;var __l=__k instanceof Array ? __k : Object.getOwnPropertyNames(__k||{});var __n=__l.length;for (var __m=0;__m<__n;__m++){var __j=(__l===__k)?__m:__l[__m];var v=__k[__j];	actual_args.push(args)}
		var start=args.length;
		while ((start < meta.arity)) 
		{
			var arg=meta.arguments[start];
			actual_args.push(extra[arg.name]);
			start = (start + 1);
		}
		return f.apply(t, actual_args);
	}
extend.str=	function(v){
		var self=extend;
		if ( extend.isString(v) )
		{
			return v;
		}
		else
		{
			return JSON.stringify(v);
		}
	}
extend.range=	function(start, end, step){
		// Creates a new list composed of elements in the given range, determined by
		// the 'start' index and the 'end' index. This function will automatically
		// find the proper step (wether '+1' or '-1') depending on the bounds you
		// specify.
		var self=extend;
		if (step === undefined) {step=1}
		var result=[];
		 if (!extend.isDefined(end)) {
		   if (extend.isList(start)) {end=start[1];start=start[0];}
		   else                      {end=start;start=0;}
		 }
		 if (start < end ) {
		   for ( var i=start ; i<end ; i+=step ) {
		     result.push(i);
		   }
		 }
		 else if (start > end ) {
		   for ( var i=start ; i>end ; i-=step ) {
		     result.push(i);
		   }
		 }
		
		return result;
	}
extend.sliceArguments=	function(args, index){
		// This is a utility function that will return the rest of the given
		// arguments list, without using the 'slice' operation which is only
		// available to arrays.
		var self=extend;
		var res=[];
		 while (index<args.length) { res.push(args[index++]) }
		
		return res;
	}
extend.len=	function(value){
		var self=extend;
		return  value && value != "" && (value instanceof Array ? value.length : (value.length || Object.getOwnPropertyNames(value).length)) || 0;
		
	}
extend.access=	function(value, index){
		var self=extend;
		if ( (index >= 0) )
		{
			return value[index]
			
		}
		else
		{
			if ( (((typeof(value) == "string") || extend.isList(value)) || (value && extend.isNumber(value.length))) )
			{
				return value[value.length + index]
				
			}
			else
			{
				throw ("extend.access:Type not supported:" + value);
			}
		}
	}
extend.offset=	function(value, index){
		var self=extend;
		if ( (index >= 0) )
		{
			return index;
		}
		else
		{
			return (extend.len(value) + index);
		}
	}
extend.iterate=	function(value, callback, context){
		// Iterates on the given values. If 'value' is an array, the _callback_ will be
		// invoked on each item (giving the 'value[i], i' as argument) until the callback
		// returns 'false'. If 'value' is a dictionary, the callback will be applied
		// on the values (giving 'value[k], k' as argument). Otherwise the object is
		// expected to define both '__len__' and '__item__' to
		// enable the iteration.
		var self=extend;
		  if ( !value ) { return }
		  // We use foreach if it's available
		  var result      = undefined;
		  if ( value.forEach ) {
		       try {result=value.forEach(callback)} catch (e) {
		           if      ( e === extend.FLOW_CONTINUE ) {}
		           else if ( e === extend.FLOW_BREAK    ) {return e}
		           else if ( e === extend.FLOW_RETURN   ) {return e}
		           else    { extend.exception(e) ; throw e}
		       }
		  } else if ( value.length != undefined ) {
		    var length = undefined;
		    // Is it an object with the length() and get() protocol ?
		    if ( typeof(value.__len__) == "function" && typeof(value.__getitem__) == "function" ) {
		      length = value.__len__()
		      for ( var i=0 ; i<length ; i++ ) {
		          try {result=callback.call(context, value.__getitem__(i), i);} catch (e) {
		              if      ( e === extend.FLOW_CONTINUE ) {}
		              else if ( e === extend.FLOW_BREAK    ) {return e}
		              else if ( e === extend.FLOW_RETURN   ) {return e}
		              else    { extend.exception(e) ; throw e}
		          }
		      }
		    // Or a plain array ?
		    } else {
		      length = value.length;
		      for ( var i=0 ; i<length ; i++ ) {
		          var result = undefined;
		          try {result=callback.call(context, value[i], i);} catch (e) {
		              if      ( e === extend.FLOW_CONTINUE ) {}
		              else if ( e === extend.FLOW_BREAK    ) {return e}
		              else if ( e === extend.FLOW_RETURN   ) {return e}
		              else    { extend.exception(e) ; throw e}
		          }
		      }
		    }
		  } else {
		    for ( var k in value ) {
		       var result = undefined;
		       try {result=callback.call(context, value[k], k);} catch (e) {
		          if      ( e === extend.FLOW_CONTINUE ) {}
		          else if ( e === extend.FLOW_BREAK    ) {return e}
		          else if ( e === extend.FLOW_RETURN   ) {return e}
		          else    { extend.exception(e) ; throw e}
		       }
		    }
		  }
		  if (!(result===undefined)) {return result}
		
	}
extend.keys=	function(value){
		var self=extend;
		if ( (((((value === null) || (value === undefined)) || (value === true)) || ((value === false) || extend.isString(value))) || extend.isNumber(value)) )
		{
			return null;
		}
		else if ( extend.isList(value) )
		{
			var l=value.length;
			var i=0;
			var r=new Array(value.length);
			while ((i < l)) 
			{
				r[i] = i;
				i = (i + 1);
			}
			return r;
		}
		else
		{
			return Object.getOwnPropertyNames(value);
		}
	}
extend.values=	function(value){
		var self=extend;
		if ( (extend.isString(value) || extend.isNumber(value)) )
		{
			return null;
		}
		else if ( extend.isList(value) )
		{
			return [].concat(value);
		}
		else
		{
			var res=[];
			for(var k in value) { res.push(value[k]); }
			
			return res;
		}
	}
extend.items=	function(value){
		var self=extend;
		if ( (extend.isString(value) || extend.isNumber(value)) )
		{
			return null;
		}
		else if ( extend.isList(value) )
		{
			return extend.map(value, function(v, i){
				return {"key":i, "value":v};
			});
		}
		else
		{
			var res=[];
			for (var k in value) { res.push({key:k,value:value[k]}); }
			
			return res;
		}
	}
extend.pairs=	function(value){
		// Returns (key, value) pairs
		var self=extend;
		if ( (extend.isString(value) || extend.isNumber(value)) )
		{
			return null;
		}
		else if ( extend.isList(value) )
		{
			return extend.map(value, function(v, i){
				return [i, v];
			});
		}
		else
		{
			var res=[];
			var __o=value;var __p=__o instanceof Array ? __o : Object.getOwnPropertyNames(__o||{});var __r=__p.length;for (var __q=0;__q<__r;__q++){var i=(__p===__o)?__q:__p[__q];var v=__o[i];	res.push([i, v])}
			return res;
		}
	}
extend.greater=	function(a, b){
		var self=extend;
		return (extend.cmp(a, b) > 0);
	}
extend.smaller=	function(a, b){
		var self=extend;
		return (extend.cmp(a, b) < 0);
	}
extend.cmp=	function(a, b){
		// Compares the given values, with the following semantics:
		// 
		// - Arrays: will compare each value, returning the result for the
		// first non-zero comparison
		// - Maps: will compare all the  values that are defined in both
		// - Strings: use `localeCompare`
		var self=extend;
		if ( extend.isList(a) )
		{
			if ( extend.isList(b) )
			{
				var la=extend.len(a);
				var lb=extend.len(b);
				var l=Math.max(la, lb);
				var res=0;
				var i=0;
				while (((res == 0) && (i < l))) 
				{
					res = extend.cmp(a[i], b[i]);
					i = (i + 1);
				}
				return res;
			}
			else if ( (extend.len(a) > extend.len(b)) )
			{
				return 1;
			}
			else
			{
				return -1;
			}
		}
		else if ( extend.isMap(a) )
		{
			if ( extend.isMap(b) )
			{
				var res=0;
				var __s=a;var __t=__s instanceof Array ? __s : Object.getOwnPropertyNames(__s||{});var __v=__t.length;for (var __u=0;__u<__v;__u++){var k=(__t===__s)?__u:__t[__u];var va=__s[k];	var vb=b[k];
					if ( (! extend.isDefined(va)) )
					{
						res = -1;
					}
					else if ( (! extend.isDefined(vb)) )
					{
						res = 1;
					}
					else
					{
						res = extend.cmp(va, vb);
					}
					if ( (res != 0) )
					{
						break
					}}
				if ( (res == 0) )
				{
					var __w=b;var __x=__w instanceof Array ? __w : Object.getOwnPropertyNames(__w||{});var __z=__x.length;for (var __y=0;__y<__z;__y++){var k=(__x===__w)?__y:__x[__y];var vb=__w[k];	var va=a[k];
						if ( (! extend.isDefined(va)) )
						{
							res = -1;
						}
						else if ( (! extend.isDefined(vb)) )
						{
							res = 1;
						}
						else
						{
							res = extend.cmp(va, vb);
						}
						if ( (res != 0) )
						{
							break
						}}
				}
				return res;
			}
			else if ( (extend.len(a) > extend.len(b)) )
			{
				return 1;
			}
			else
			{
				return -1;
			}
		}
		else if ( ((extend.isString(a) && extend.isString(b)) && extend.isDefined(a.localeCompare)) )
		{
			return a.localeCompare(b);
		}
		else if ( (a === null) )
		{
			if ( (b === null) )
			{
				return 0;
			}
			else if ( (b === undefined) )
			{
				return 1;
			}
			else
			{
				return -1;
			}
		}
		else if ( (a === undefined) )
		{
			if ( (b === undefined) )
			{
				return 0;
			}
			else
			{
				return -1;
			}
		}
		else
		{
			if ( (a === b) )
			{
				return 0;
			}
			else if ( (a == b) )
			{
				return 0;
			}
			else if ( (a === extend.Nothing) )
			{
				return -1;
			}
			else if ( (b === extend.Nothing) )
			{
				return 1;
			}
			else if ( (a > b) )
			{
				return 1;
			}
			else if ( (a < b) )
			{
				return -1;
			}
			else if ( (! extend.isDefined(b)) )
			{
				return 1;
			}
			else if ( (! extend.isDefined(a)) )
			{
				return -1;
			}
			else
			{
				return -2;
			}
		}
	}
extend.reverse=	function(value){
		var self=extend;
		var l=value.length;
		var r=new Array();
		var __A=value;var __B=__A instanceof Array ? __A : Object.getOwnPropertyNames(__A||{});var __D=__B.length;for (var __C=0;__C<__D;__C++){var i=(__B===__A)?__C:__B[__C];var v=__A[i];	r[(l - i)] = v}
		return r;
	}
extend.sorted=	function(value, comparison, reverse){
		var self=extend;
		if (comparison === undefined) {comparison=extend.cmp}
		if (reverse === undefined) {reverse=false}
		if ( extend.isList(comparison) )
		{
			var l=(extend.len(comparison) - 1);
			var c=function(a, b){
				var total=0;
				var __E=comparison;var __F=__E instanceof Array ? __E : Object.getOwnPropertyNames(__E||{});var __H=__F.length;for (var __G=0;__G<__H;__G++){var i=(__F===__E)?__G:__F[__G];var extractor=__E[i];	var va=extractor(a);
					var vb=extractor(b);
					var v=(extend.cmp(va, vb) * Math.pow(10, (l - i)));
					total = (total + v)}
				return total;
			};
			return extend.sorted(value, c, reverse);
		}
		else
		{
			if ( extend.isList(value) )
			{
				value = extend.copy(value);
				value.sort(comparison);
				if ( reverse )
				{
					value.reverse();
				}
				return value;
			}
			else if ( extend.isMap(value) )
			{
				return extend.sorted(extend.values(value), extend.cmp, reverse);
			}
			else if ( (extend.isNumber(value) || extend.isString(value)) )
			{
				return value;
			}
			else if ( (! value) )
			{
				return value;
			}
			else
			{
				throw "Not implemented";
			}
		}
	}
extend.copy=	function(value, depth){
		var self=extend;
		if (depth === undefined) {depth=1}
		if ( ((((! extend.isDefined(value)) || (value === false)) || (value === true)) || (value === null)) )
		{
			return value;
		}
		else if ( (depth < 1) )
		{
			return value;
		}
		else if ( extend.isList(value) )
		{
			if ( (depth <= 1) )
			{
				if ( (value && value.concat) )
				{
					return [].concat(value);
				}
				else
				{
					return extend.map(value, function(_){
						return _;
					});
				}
			}
			else
			{
				return extend.map(value, function(_){
					return extend.copy(_, (depth - 1));
				});
			}
		}
		else if ( extend.isObject(value) )
		{
			var r={};
			for (var k in value) {
			if (depth <= 1) { r[k]=value[k]; }
			else            { r[k]=extend.copy(value[k], depth - 1); }
			}
			
			return r;
		}
		else
		{
			return value;
		}
	}
extend.merge=	function(value, otherValue, replace){
		var self=extend;
		if (replace === undefined) {replace=false}
		if ( extend.isList(value) )
		{
			!(extend.isList(otherValue)) && extend.assert(false, "extend.merge:", "extend.merge(a,b) b expected to be a list", "(failed `extend.isList(otherValue)`)");
			var __J=otherValue;var __K=__J instanceof Array ? __J : Object.getOwnPropertyNames(__J||{});var __M=__K.length;for (var __L=0;__L<__M;__L++){var __I=(__K===__J)?__L:__K[__L];var v=__J[__I];	if ( (extend.find(value, v) == -1) )
				{
					value.push(v);
				}}
		}
		else if ( extend.isMap(value) )
		{
			!(extend.isMap(otherValue)) && extend.assert(false, "extend.merge:", "extend.merge(a,b) b expected to be a map", "(failed `extend.isMap(otherValue)`)");
			var __N=otherValue;var __O=__N instanceof Array ? __N : Object.getOwnPropertyNames(__N||{});var __Q=__O.length;for (var __P=0;__P<__Q;__P++){var k=(__O===__N)?__P:__O[__P];var v=__N[k];	if ( ((! extend.isDefined(value[k])) || replace) )
				{
					value[k] = v;
				}}
		}
		else if ( value )
		{
			extend.error("extend.merge(a,_) expects a to be a list or a map");
		}
		return value;
	}
extend.couplesAsMap=	function(value){
		var self=extend;
		if ( extend.isList(value) )
		{
			var r={};
			var __R=value;var __S=__R instanceof Array ? __R : Object.getOwnPropertyNames(__R||{});var __U=__S.length;for (var __T=0;__T<__U;__T++){var k=(__S===__R)?__T:__S[__T];var v=__R[k];	r[v[0]] = v[1]}
			return r;
		}
		else
		{
			extend.error("couplesAsMap: expects [[<key>, <value>]] as input, got", value);
			return null;
		}
	}
extend.itemsAsMap=	function(value){
		var self=extend;
		if ( extend.isList(value) )
		{
			var r={};
			var __V=value;var __W=__V instanceof Array ? __V : Object.getOwnPropertyNames(__V||{});var __Y=__W.length;for (var __X=0;__X<__Y;__X++){var k=(__W===__V)?__X:__W[__X];var v=__V[k];	r[v.key] = v.value}
			return r;
		}
		else
		{
			extend.error("itemsAsMap: expects [[{key:<key>, value:<value>}] as input, got", value);
			return null;
		}
	}
extend.find=	function(enumerable, value){
		// Returns the index of the first element that equals the given value
		// Returns -1 if not found.
		var self=extend;
		var found=-1;
		var __Z=enumerable;var __0=__Z instanceof Array ? __Z : Object.getOwnPropertyNames(__Z||{});var __2=__0.length;for (var __1=0;__1<__2;__1++){var k=(__0===__Z)?__1:__0[__1];var v=__Z[k];	if ( ((v == value) && (found == -1)) )
			{
				found = k;
				break
			}}
		return found;
	}
extend.insert=	function(enumerable, position, value){
		var self=extend;
		if ( extend.isList(enumerable) )
		{
			enumerable.splice(position, 0, value);
			return enumerable;
		}
		else
		{
			extend.error("extend.add: Type not supported", enumerable);
			return null;
		}
	}
extend.add=	function(enumerable, value){
		var self=extend;
		if ( extend.isList(enumerable) )
		{
			enumerable.push(value);
			return enumerable;
		}
		else
		{
			extend.error("extend.add: Type not supported", enumerable);
			return null;
		}
	}
extend.remove=	function(enumerable, value){
		// Removes the given value from the list or map
		var self=extend;
		if ( extend.isList(enumerable) )
		{
			var index=extend.find(enumerable, value);
			if ( (index >= 0) )
			{
				enumerable.splice(index, 1);
			}
			return enumerable;
		}
		else if ( extend.isMap(enumerable) )
		{
			var k=extend.keys(enumerable);
			var __4=k;var __5=__4 instanceof Array ? __4 : Object.getOwnPropertyNames(__4||{});var __7=__5.length;for (var __6=0;__6<__7;__6++){var __3=(__5===__4)?__6:__5[__6];var _=__4[__3];	if ( (_ == value) )
				{
					delete enumerable[_];
					
				}}
			return enumerable;
		}
		else
		{
			return enumerable;
		}
	}
extend.removeAt=	function(enumerable, index){
		// Removes the element at the given index, returning the updated enumerable.
		var self=extend;
		if ( extend.isList(enumerable) )
		{
			if ( ((index >= 0) && (index < extend.len(enumerable))) )
			{
				enumerable.splice(index, 1);
			}
			return enumerable;
		}
		else if ( extend.isMap(enumerable) )
		{
			delete enumerable[index];
			
			return enumerable;
		}
		else
		{
			return enumerable;
		}
	}
extend.findLike=	function(enumerable, predicate){
		// Returns the index of the first element that matches the given predicate.
		// Returns -1 if not found.
		var self=extend;
		var found=-1;
		var __8=enumerable;var __9=__8 instanceof Array ? __8 : Object.getOwnPropertyNames(__8||{});var __ab=__9.length;for (var __0=0;__0<__ab;__0++){var k=(__9===__8)?__0:__9[__0];var v=__8[k];	if ( (predicate(v) && (found == -1)) )
			{
				found = k;
				break
			}}
		return found;
	}
extend.findOneOf=	function(enumerable, values){
		// Find one of the `values` in the given `enumerable`, returning
		// the matching index.
		var self=extend;
		var r=-1;
		var __bb=enumerable;var __cb=__bb instanceof Array ? __bb : Object.getOwnPropertyNames(__bb||{});var __eb=__cb.length;for (var __db=0;__db<__eb;__db++){var i=(__cb===__bb)?__db:__cb[__db];var v=__bb[i];	if ( ((extend.isIn(v,values))) )
			{
				r = i;
				break
			}}
		return r;
	}
extend.first=	function(enumerable, predicate){
		// Returns the first value that matches the given predicate
		var self=extend;
		var i=extend.findLike(enumerable, predicate);
		if ( ((i === null) || (! enumerable)) )
		{
			return null;
		}
		else
		{
			return enumerable[i];
		}
	}
extend.last=	function(enumerable, predicate){
		// Returns the last value that matches the given predicate
		var self=extend;
		var res=null;
		var __fb=enumerable;var __gb=__fb instanceof Array ? __fb : Object.getOwnPropertyNames(__fb||{});var __ib=__gb.length;for (var __hb=0;__hb<__ib;__hb++){var k=(__gb===__fb)?__hb:__gb[__hb];var v=__fb[k];	if ( predicate(v) )
			{
				res = v;
			}}
		return res;
	}
extend.replace=	function(container, original, replacement){
		var self=extend;
		if ( extend.isString(container) )
		{
			while ((container.indexOf(original) != -1)) 
			{
				container = container.replace(original, replacement);
			}
		}
		else
		{
			extend.error("extend.replace only supports string for now");
		}
		return container;
	}
extend.slice=	function(value, start, end){
		var self=extend;
		if (start === undefined) {start=0}
		if (end === undefined) {end=undefined}
		if ( extend.isString(value) )
		{
			if ( (end === undefined) )
			{
				end = value.length;
			}
			if ( (start < 0) )
			{start = (value.length + start)}
			if ( (end < 0) )
			{end = (value.length + end)}
			return value.substring(start, end);
		}
		else if ( extend.isList(value) )
		{
			if ( (end === undefined) )
			{
				end = value.length;
			}
			if ( (start < 0) )
			{start = (value.length + start)}
			if ( (end < 0) )
			{end = (value.length + end)}
			return value.slice(start, end);
		}
		else if ( (extend.isObject(value) && extend.isDefined(value.length)) )
		{
			var res=[];
			if ( (end === undefined) )
			{
				end = value.length;
			}
			if ( (start < 0) )
			{start = (value.length + start)}
			if ( (end < 0) )
			{end = (value.length + end)}
			var i=start;
			while ((i < end)) 
			{
				res.push(value[i]);
			}
			return res;
		}
		else
		{
			throw ("Unsupported type for slice:" + value);
		}
	}
extend.equals=	function(a, b){
		var self=extend;
		return (a == b);
	}
extend.isIn=	function(value, list, predicate){
		// Returns true if the given value is in the given list
		var self=extend;
		if (predicate === undefined) {predicate=extend.equals}
		if ( extend.isList(list) )
		{
			 if (list.some) {
			   return list.some(function(v){return predicate(v,value)});
			 } else {
			   for ( var i=0 ; i<list.length ; i++) {
			     if (predicate(list[i],value)) { return true }
			   }
			   return false
			}
			
		}
		else if ( extend.isMap(list) )
		{
			 for ( var i in list ) {
			   if (predicate(list[i],value)) { return true }
			 }
			 return false
			
		}
		else
		{
			return false;
		}
	}
extend.difference=	function(a, b){
		// Returns the difference between a and b. Lists and maps are supported.
		var self=extend;
		if ( ((! a) || (extend.len(a) == 0)) )
		{
			return a;
		}
		if ( ((! b) || (extend.len(b) == 0)) )
		{
			return a;
		}
		if ( extend.isList(a) )
		{
			if ( extend.isMap(b) )
			{
				b = extend.values(b);
			}
			if ( extend.isList(b) )
			{
				return extend.filter(a, function(_){
					return (! ((extend.isIn(_,b))));
				});
			}
			else
			{
				extend.error(("extend.difference: Unsupported type for b, " + extend.type(b)));
				return null;
			}
		}
		else if ( extend.isMap(a) )
		{
			if ( extend.isMap(b) )
			{
				var b_keys=extend.keys(b);
				return extend.filter(a, function(_, k){
					return (! ((extend.isIn(k,b_keys))));
				});
			}
			else if ( extend.isList(b) )
			{
				return extend.filter(a, function(v){
					return (! ((extend.isIn(v,b))));
				});
			}
			else
			{
				extend.error(("extend.difference: Unsupported type for b, " + extend.type(b)));
				return null;
			}
		}
		else
		{
			extend.error(("extend.difference: Unsupported type for a, " + extend.type(a)));
			return null;
		}
	}
extend.union=	function(a, b){
		// Returns the union of a and b. Lists and maps are supported.
		var self=extend;
		if ( ((! a) || (extend.len(a) == 0)) )
		{
			return b;
		}
		if ( ((! b) || (extend.len(b) == 0)) )
		{
			return a;
		}
		if ( extend.isList(a) )
		{
			if ( extend.isMap(b) )
			{
				b = extend.values(b);
			}
			if ( extend.isList(b) )
			{
				var r=[].concat(a);
				var __kb=b;var __lb=__kb instanceof Array ? __kb : Object.getOwnPropertyNames(__kb||{});var __nb=__lb.length;for (var __mb=0;__mb<__nb;__mb++){var __jb=(__lb===__kb)?__mb:__lb[__mb];var e=__kb[__jb];	if ( (! ((extend.isIn(e,a)))) )
					{
						r.push(e);
					}}
				return r;
			}
			else
			{
				extend.error(("extend.union: Unsupported type for b, " + extend.type(b)));
			}
		}
		else if ( extend.isMap(a) )
		{
			a = extend.copy(a);
			if ( extend.isMap(b) )
			{
				return extend.merge(a, b);
			}
			else if ( extend.isList(b) )
			{
				var __ob=b;var __pb=__ob instanceof Array ? __ob : Object.getOwnPropertyNames(__ob||{});var __rb=__pb.length;for (var __qb=0;__qb<__rb;__qb++){var i=(__pb===__ob)?__qb:__pb[__qb];var v=__ob[i];	if ( (! extend.isDefined(a[i])) )
					{
						a[i] = v;
					}}
				return a;
			}
			else
			{
				extend.error(("extend.union: Unsupported type for b, " + extend.type(b)));
				return null;
			}
		}
		else
		{
			extend.error(("extend.union: Unsupported type for a, " + extend.type(a)));
			return null;
		}
	}
extend.intersection=	function(a, b){
		// Returns the intersection between a and b. Lists and maps are supported.
		var self=extend;
		if ( ((! a) || (extend.len(a) == 0)) )
		{
			return null;
		}
		else if ( extend.isList(a) )
		{
			if ( extend.isMap(b) )
			{
				return extend.filter(a, function(_, i){
					return extend.isDefined(b[k]);
				});
			}
			else
			{
				return extend.filter(a, function(_, i){
					return ((extend.isIn(_,b)));
				});
			}
		}
		else if ( extend.isMap(a) )
		{
			if ( extend.isMap(b) )
			{
				return extend.reduce(b, function(r, v, k){
					if ( extend.isDefined(a[k]) )
					{r[k] = v}
				}, {});
			}
			else if ( extend.isList(b) )
			{
				return extend.reduce(b, function(r, k){
					var v=a[k];
					if ( extend.isDefined(v) )
					{r[k] = v}
				}, {});
			}
			else
			{
				extend.error("extend.intersection: Type for b not supported", extend.type(b));
			}
		}
		else
		{
			return extend.error("NotImplemented");
		}
	}
extend.createMapFromItems=	function(items){
		var self=extend;
		items = extend.sliceArguments(arguments,0)
		 var result = {}
		 for ( var i=0 ; i<items.length ; i++ ) {
		   result[items[i][0]] = items[i][1]
		 }
		 return result
		
	}
extend.type=	function(value){
		var self=extend;
		return typeof(value);
	}
extend.isDefined=	function(value){
		var self=extend;
		return (! (value === undefined));
	}
extend.isUndefined=	function(value){
		var self=extend;
		return (value === undefined);
	}
extend.isList=	function(value){
		var self=extend;
		if (typeof(Float64Array)!="undefined") {
		return (
		value instanceof Array        ||
		value instanceof Float32Array ||
		value instanceof Float64Array ||
		value instanceof Int8Array    ||
		value instanceof Int16Array   ||
		value instanceof Int32Array
		);
		} else {
		return (value instanceof Array);
		}
		
	}
extend.isNumber=	function(value){
		var self=extend;
		return (typeof(value) == "number");
	}
extend.isString=	function(value){
		var self=extend;
		return (typeof(value) == "string");
	}
extend.isMap=	function(value){
		var self=extend;
		 return !!(!(value===null) && typeof value == "object" && !extend.isList(value))
		
	}
extend.isIterable=	function(value){
		// The value needs to be an array or an object with
		var self=extend;
		 return extend.isList(value) || extend.isMap(value) || value && typeof (value.length) == "number";
		
	}
extend.isFunction=	function(value){
		var self=extend;
		 return !!(typeof value == "function")
		
	}
extend.isObject=	function(value){
		var self=extend;
		 return !!(typeof value == "object")
		
	}
extend.isInstance=	function(value, ofClass){
		// Tells if the given value is an instance (in the sense of extend) of the
		// given 'ofClass'. If there is no given class, then it will just return
		// true if the value is an instance of any class.
		var self=extend;
		if (ofClass === undefined) {ofClass=undefined}
		if ( ofClass )
		{
			var is_instance=false;
			is_instance = value instanceof ofClass;
			
			return (((value && extend.isDefined(value.getClass)) && value.isInstance(ofClass)) || is_instance);
		}
		else
		{
			return (value && extend.isDefined(value.getClass));
		}
	}
extend.getType=	function(value){
		// Returns the type of the given value
		var self=extend;
		if ( (! extend.isDefined(value)) )
		{
			return extend.Type.Undefined;
		}
		else if ( (value === null) )
		{
			return extend.Type.None;
		}
		else if ( extend.isNumber(value) )
		{
			return extend.Type.Number;
		}
		else if ( extend.isString(value) )
		{
			return extend.Type.String;
		}
		else if ( extend.isList(value) )
		{
			return extend.Type.List;
		}
		else if ( extend.isMap(value) )
		{
			return extend.Type.Map;
		}
		else if ( extend.isFunction(value) )
		{
			return extend.Type.Function;
		}
		else if ( extend.isObject(value) )
		{
			if ( extend.isFunction(value.getClass) )
			{
				return extend.Type.Instance;
			}
			else
			{
				return extend.Type.Object;
			}
		}
		else
		{
			return extend.Type.Unknown;
		}
	}
extend.getMethodOf=	function(instance, name){
		var self=extend;
		return instance[name];
	}
extend.getClassOf=	function(instance){
		var self=extend;
		// Unable to embed the following code
		// return getDefinitionByName(getQualifiedSuperclassName(instance));
		// 
		return instance.getClass()
		
	}
extend.print=	function(args){
		// Prints the given arguments to the JavaScript console (available in Safari
		// and in Mozilla if you've installed FireBug), or using the 'print' command
		// in SpiderMonkey. If neither 'console' or 'print' is defined,
		// this won't do anything.
		// 
		// When objects are given as arguments, they will be printed using the
		// 'toSource' method they offer.
		// 
		// Example:
		// 
		// >    extend print ("Here is a dict:", {a:1,b:2,c:3})
		// 
		// will output
		// 
		// >    "Here is a dict: {a:1,b:2,c:3}"
		var self=extend;
		args = extend.sliceArguments(arguments,0)
		var pr_func=eval("print");
		if ( (((typeof(console) == "undefined") && (typeof(pr_func) === "undefined")) && (extend.PrintCallback === undefined)) )
		{
			return null;
		}
		var res="";
		 for ( var i=0 ; i<args.length ; i++ ) {
		   var val = args[i]
		   if ( val!=undefined && typeof(val) == "object" && val.toSource != undefined) { val = val.toSource() }
		   if ( i<args.length-1 ) { res += val + " " }
		   else { res += val }
		 }
		
		if ( (extend.PrintCallback === undefined) )
		{
			if ( (typeof(console) != "undefined") )
			{
				if ( extend.isDefined(console.log.apply) )
				{
					console.log.apply(console, args);
				}
				else
				{
					console.log(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7]);
				}
			}
			else if ( ((typeof(document) == "undefined") && (typeof(pr_func) != "undefined")) )
			{
				pr_func(res);
			}
		}
		else
		{
			extend.PrintCallback(res);
		}
		return args;
	}
extend.warning=	function(message){
		var self=extend;
		message = extend.sliceArguments(arguments,0)
		if ( extend.WarningCallback )
		{
			extend.WarningCallback.apply(extend, message);
		}
		else if ( extend.isDefined(console) )
		{
			if ( extend.isDefined(console.warn.apply) )
			{
				console.warn.apply(console, message);
			}
			else
			{
				console.warn(message[0], message[1], message[2], message[3], message[4], message[5], message[6], message[7]);
			}
		}
		else
		{
			extend.print.apply(extend, ["[!] "].concat(message));
		}
		return message;
	}
extend.error=	function(message){
		var self=extend;
		message = extend.sliceArguments(arguments,0)
		if ( extend.ErrorCallback )
		{
			extend.ErrorCallback.apply(extend, message);
		}
		else if ( extend.isDefined(console) )
		{
			if ( extend.isDefined(console.error.apply) )
			{
				console.error.apply(console, message);
			}
			else
			{
				console.error(message[0], message[1], message[2], message[3], message[4], message[5], message[6], message[7]);
			}
		}
		else
		{
			extend.print.apply(extend, ["[!] "].concat(message));
		}
		return message;
	}
extend.debug=	function(message){
		var self=extend;
		message = extend.sliceArguments(arguments,0)
		if ( extend.DebugCallback )
		{
			extend.DebugCallback.apply(extend, message);
		}
		else if ( extend.isDefined(console) )
		{
			console.debug.apply(console, message);
		}
		else
		{
			extend.print.apply(extend, ["[!] "].concat(message));
		}
		return message;
	}
extend.exception=	function(e, message){
		var self=extend;
		message = extend.sliceArguments(arguments,1)
		var m=[];
		var __tb=message;var __ub=__tb instanceof Array ? __tb : Object.getOwnPropertyNames(__tb||{});var __wb=__ub.length;for (var __vb=0;__vb<__wb;__vb++){var __sb=(__ub===__tb)?__vb:__ub[__vb];var _=__tb[__sb];	m.push(_)}
		if ( (extend.len(m) == 0) )
		{
			m.push("Extend: exception intercepted");
		}
		m.push(e);
		if ( extend.ExceptionCallback )
		{
			extend.ExceptionCallback.apply(extend, m);
		}
		else if ( extend.isDefined(console) )
		{
			if ( extend.isDefined(console.error.apply) )
			{
				console.error.apply(console, m);
			}
			else
			{
				console.error(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7]);
			}
		}
		else
		{
			extend.print.apply(extend, m);
		}
		return e;
	}
extend.assert=	function(predicate, message){
		var self=extend;
		message = extend.sliceArguments(arguments,1)
		if ( (! predicate) )
		{
			extend.error.apply(extend, message);
		}
		return message;
	}
extend.fail=	function(message){
		var self=extend;
		message = extend.sliceArguments(arguments,0)
		extend.error.apply(extend, message);
		return false;
	}
extend.sprintf=	function(){
		var self=extend;
		var str_repeat  = function(i, m){ for (var o = []; m > 0; o[--m] = i); return(o.join(''));};
		var i = 0, a, f = arguments[i++], o = [], m, p, c, x;
		while (f) {
		  if (m = /^[^\x25]+/.exec(f)) o.push(m[0]);
		  else if (m = /^\x25{2}/.exec(f)) o.push('%');
		  else if (m = /^\x25(?:(\d+)\$)?(\+)?(0|'[^$])?(-)?(\d+)?(?:\.(\d+))?([b-fosuxX])/.exec(f)) {
		    if (((a = arguments[m[1] || i++]) == null) || (a == undefined)) throw("Too few arguments.");
		    if (/[^s]/.test(m[7]) && (typeof(a) != 'number'))
		      throw("Expecting number but found " + typeof(a));
		    switch (m[7]) {
		      case 'b': a = a.toString(2); break;
		      case 'c': a = String.fromCharCode(a); break;
		      case 'd': a = parseInt(a); break;
		      case 'e': a = m[6] ? a.toExponential(m[6]) : a.toExponential(); break;
		      case 'f': a = m[6] ? parseFloat(a).toFixed(m[6]) : parseFloat(a); break;
		      case 'o': a = a.toString(8); break;
		      case 's': a = ((a = String(a)) && m[6] ? a.substring(0, m[6]) : a); break;
		      case 'u': a = Math.abs(a); break;
		      case 'x': a = a.toString(16); break;
		      case 'X': a = a.toString(16).toUpperCase(); break;
		    }
		    a = (/[def]/.test(m[7]) && m[2] && a > 0 ? '+' + a : a);
		    c = m[3] ? m[3] == '0' ? '0' : m[3].charAt(1) : ' ';
		    x = m[5] - String(a).length;
		    p = m[5] ? str_repeat(c, x) : '';
		    o.push(m[4] ? a + p : p + a);
		  }
		  else {throw ("Huh ?!");}
		  f = f.substring(m[0].length);
		}
		return o.join('');
		
	}
extend.Registry={}
extend.getClass=	function(name){
		var self=extend;
		return extend.Registry[name];
	}
extend.getParentClass=	function(object){
		var self=extend;
		return extend.Registry[name];
	}
extend.getClasses=	function(){
		var self=extend;
		return extend.Registry;
	}
extend.getMethod=	function(name, object){
		var self=extend;
	}
extend.getSuperMethod=	function(name, object){
		var self=extend;
	}
extend.getChildrenOf=	function(aClass){
		var self=extend;
		var res={};
		var values = extend.getClasses()
		for ( key in values ) {
			if ( values[key] != aClass && values[key].isSubclassOf(aClass) )
			{ res[key] = values[key] }
		}
		
		return res;
	}
extend.strip=	function(value){
		var self=extend;
		return value.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
		
	}
extend.car=	function(list){
		var self=extend;
		if ( (list.length > 0) )
		{
			return list[0];
		}
		else
		{
			return null;
		}
	}
extend.cdr=	function(list){
		var self=extend;
		if ( (list.length == 0) )
		{
			return null;
		}
		else if ( (list.length == 1) )
		{
			return [];
		}
		else
		{
			return extend.slice(list,1,undefined);
		}
	}
extend.asMap=	function(iterable, extractor, replacer){
		// Converts the given iterable where the key is extracted by the given
		// `extractor`. If `replacer` is defined and there is already an element
		// with the given key, then `replacer` will be called.
		var self=extend;
		if (replacer === undefined) {replacer=undefined}
		var res={};
		var __xb=iterable;var __yb=__xb instanceof Array ? __xb : Object.getOwnPropertyNames(__xb||{});var __Ab=__yb.length;for (var __zb=0;__zb<__Ab;__zb++){var key=(__yb===__xb)?__zb:__yb[__zb];var value=__xb[key];	key = extractor(value, key)
			if ( (extend.isDefined(res[key]) && extend.isDefined(replacer)) )
			{
				res[key] = replacer(value, res[key], key);
			}
			else
			{
				res[key] = value;
			}}
		return res;
	}
extend.map=	function(iterable, callback){
		var self=extend;
		var result=null;
		if ( extend.isList(iterable) )
		{
			result = new Array(extend.len(iterable));
			var __Bb=iterable;var __Cb=__Bb instanceof Array ? __Bb : Object.getOwnPropertyNames(__Bb||{});var __Eb=__Cb.length;for (var __Db=0;__Db<__Eb;__Db++){var i=(__Cb===__Bb)?__Db:__Cb[__Db];var v=__Bb[i];	result[i] = callback(v, i, iterable)}
		}
		else
		{
			result = {};
			var __Fb=iterable;var __Gb=__Fb instanceof Array ? __Fb : Object.getOwnPropertyNames(__Fb||{});var __Ib=__Gb.length;for (var __Hb=0;__Hb<__Ib;__Hb++){var k=(__Gb===__Fb)?__Hb:__Gb[__Hb];var v=__Fb[k];	result[k] = callback(v, k, iterable)}
		}
		return result;
	}
extend.map0=	function(iterable, callback){
		var self=extend;
		return extend.map(iterable, function(){
			return callback();
		});
	}
extend.map1=	function(iterable, callback){
		var self=extend;
		return extend.map(iterable, function(_){
			return callback(_);
		});
	}
extend.map2=	function(iterable, callback){
		var self=extend;
		return extend.map(iterable, function(a, b){
			return callback(a, b);
		});
	}
extend.map3=	function(iterable, callback){
		var self=extend;
		return extend.map(iterable, function(a, b){
			return callback(a, b, iterable);
		});
	}
extend.filter=	function(iterable, callback, processor){
		var self=extend;
		var result=null;
		if ( extend.isList(iterable) )
		{
			if ( ((! processor) && iterable.filter) )
			{
				result = iterable.filter(callback);
			}
			else
			{
				result = [];
				var __Jb=iterable;var __Kb=__Jb instanceof Array ? __Jb : Object.getOwnPropertyNames(__Jb||{});var __Mb=__Kb.length;for (var __Lb=0;__Lb<__Mb;__Lb++){var k=(__Kb===__Jb)?__Lb:__Kb[__Lb];var e=__Jb[k];	if ( callback(e, k) )
					{
						if ( processor )
						{
							e = processor(e, k);
						}
						result.push(e);
					}}
			}
		}
		else if ( extend.isMap(iterable) )
		{
			result = {};
			var __Nb=iterable;var __Ob=__Nb instanceof Array ? __Nb : Object.getOwnPropertyNames(__Nb||{});var __Qb=__Ob.length;for (var __Pb=0;__Pb<__Qb;__Pb++){var k=(__Ob===__Nb)?__Pb:__Ob[__Pb];var e=__Nb[k];	if ( callback(e, k) )
				{
					if ( processor )
					{e = processor(e, k)}
					result[k] = e;
				}}
		}
		else if ( extend.isIterable(iterable) )
		{
			result = [];
			var __Rb=iterable;var __Sb=__Rb instanceof Array ? __Rb : Object.getOwnPropertyNames(__Rb||{});var __Ub=__Sb.length;for (var __Tb=0;__Tb<__Ub;__Tb++){var k=(__Sb===__Rb)?__Tb:__Sb[__Tb];var e=__Rb[k];	if ( callback(e, k) )
				{
					if ( processor )
					{e = processor(e, k)}
					result.push(e);
				}}
		}
		else
		{
			result = {};
			var __Vb=iterable;var __Wb=__Vb instanceof Array ? __Vb : Object.getOwnPropertyNames(__Vb||{});var __Yb=__Wb.length;for (var __Xb=0;__Xb<__Yb;__Xb++){var k=(__Wb===__Vb)?__Xb:__Wb[__Xb];var e=__Vb[k];	if ( callback(e, k) )
				{
					if ( processor )
					{e = processor(e, k)}
					result[k] = e;
				}}
		}
		return result;
	}
extend.reduce=	function(iterable, callback, initial){
		var self=extend;
		if (initial === undefined) {initial=undefined}
		var res=initial;
		var i=0;
		var __Zb=iterable;var __0b=__Zb instanceof Array ? __Zb : Object.getOwnPropertyNames(__Zb||{});var __2b=__0b.length;for (var __1b=0;__1b<__2b;__1b++){var k=(__0b===__Zb)?__1b:__0b[__1b];var e=__Zb[k];	var r=undefined;
			if ( ((i == 0) && (! extend.isDefined(res))) )
			{
				r = e;
			}
			else
			{
				r = callback(res, e, k, i);
			}
			if ( extend.isDefined(r) )
			{
				res = r;
			}
			i = (i + 1)}
		return res;
	}
extend.foldl=	function(iterable, seed, callback){
		// An alias to reduce, with different parameter ordering. Preserved for
		// compatibility.
		var self=extend;
		return extend.reduce(iterable, callback, seed);
	}
extend.extendPrimitiveTypes=	function(){
		var self=extend;
		String.prototype.__len__ = function(){
			return this.length;
		};
		Array.prototype.extend = function(array){
			var __4b=array;var __5b=__4b instanceof Array ? __4b : Object.getOwnPropertyNames(__4b||{});var __7b=__5b.length;for (var __6b=0;__6b<__7b;__6b++){var __3b=(__5b===__4b)?__6b:__5b[__6b];var e=__4b[__3b];	this.append(e)}
		};
		Array.prototype.append = function(e){
			return this.push(e);
		};
		Array.prototype.insert = function(e, i){
			return this.splice(i, e);
		};
		Array.prototype.slice = function(){
		};
		Array.prototype.__iter__ = function(){
			return this.length;
		};
		Array.prototype.__len__ = function(){
			return this.length;
		};
		Object.prototype.keys = function(){
			var result=[];
			for (var k in this) { var key=k ; result.push(key) }
			
			return result;
		};
		Object.prototype.items = function(){
			var result=[];
			for (var k in this) { var key=k ; result.push([key,this[key]]) }
			
			return result;
		};
		Object.prototype.values = function(){
			var result=[];
			for (var k in this) { var key=k ; result.push([key,this[key]]) }
			
			return result;
		};
		Object.prototype.hasKey = function(key){
			return (typeof(this[key]) != "undefined");
		};
		Object.prototype.get = function(key){
			return this[key];
		};
		Object.prototype.set = function(key, value){
			this[key] = value;
			return this;
		};
		Object.prototype.setDefault = function(key, value){
			if ( (typeof(this[key]) != "undefined") )
			{
				return this[key];
			}
			else
			{
				this[key] = value;
				return value;
			}
		};
		Object.prototype.__iter__ = function(){
		};
		Object.prototype.__len__ = function(){
			return this.keys().length;
		};
	}
extend.init=	function(){
		var self=extend;
	}
if (typeof(extend.init)!="undefined") {extend.init();}
})(extend);
