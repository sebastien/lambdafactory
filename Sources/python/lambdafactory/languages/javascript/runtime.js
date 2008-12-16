
var extend=extend||{}
var __this__=extend
extend.__VERSION__='2.2.0';extend.Counters={'Instances':0}
extend.Class=function(declaration){var __this__=extend;var full_name=declaration.name;var class_object=function(){if((!((arguments.length==1)&&(arguments[0]=='__Extend_SubClass__'))))
{var properties=class_object.listProperties()
for(var prop in properties){this[prop]=properties[prop];}
if(this.initialize)
{return this.initialize.apply(this,arguments)}}};class_object.isClass=function(){return true};class_object._parent=declaration.parent;class_object._name=declaration.name;class_object._properties={'all':{},'inherited':{},'own':{}};class_object._shared={'all':{},'inherited':{},'own':{}};class_object._operations={'all':{},'inherited':{},'own':{},'fullname':{}};class_object._methods={'all':{},'inherited':{},'own':{},'fullname':{}};class_object.getName=function(){return class_object._name};class_object.getParent=function(){return class_object._parent};class_object.isSubclassOf=function(c){var parent=this;while(parent)
{if((parent==c))
{return true}
parent=parent.getParent();}
return false};class_object.hasInstance=function(o){return o.getClass().isSubclassOf(class_object)};class_object.bindMethod=function(object,methodName){var this_method=object[methodName];return function(){var a=arguments;if((a.length==0))
{return this_method.call(object)}
else if((a.length==1))
{return this_method.call(object,a[0])}
else if((a.length==2))
{return this_method.call(object,a[0],a[1])}
else if((a.length==3))
{return this_method.call(object,a[0],a[1],a[2])}
else if((a.length==4))
{return this_method.call(object,a[0],a[1],a[2],a[3])}
else if((a.length==5))
{return this_method.call(object,a[0],a[1],a[2],a[3],a[4])}
else if(true)
{var args=[];args.concat(arguments)
return this_method.apply(object,args)}}};class_object.bindCallback=function(object,methodName){var this_method=object[methodName];return function(){var a=arguments;if((a.length==0))
{return this_method.call(object,this)}
else if((a.length==1))
{return this_method.call(object,a[0],this)}
else if((a.length==2))
{return this_method.call(object,a[0],a[1],this)}
else if((a.length==3))
{return this_method.call(object,a[0],a[1],a[2],this)}
else if((a.length==4))
{return this_method.call(object,a[0],a[1],a[2],a[3],this)}
else if((a.length==5))
{return this_method.call(object,a[0],a[1],a[2],a[3],a[4],this)}
else if(true)
{var args=[];args.concat(arguments)
args.push(this)
return this_method.apply(object,args)}}};class_object.getOperation=function(name){var this_operation=class_object[name];return function(){return this_operation.apply(class_object,arguments)}};class_object.listMethods=function(o,i){if((o===undefined))
{o=true;}
if((i===undefined))
{i=true;}
if((o&&i))
{return class_object._methods.all}
else if(((!o)&&i))
{return class_object._methods.inherited}
else if((o&&(!i)))
{return class_object._methods.own}
else if(true)
{return{}}};class_object.listOperations=function(o,i){if((o===undefined))
{o=true;}
if((i===undefined))
{i=true;}
if((o&&i))
{return class_object._operations.all}
else if(((!o)&&i))
{return class_object._operations.inherited}
else if((o&&(!i)))
{return class_object._operations.own}
else if(true)
{return{}}};class_object.listShared=function(o,i){if((o===undefined))
{o=true;}
if((i===undefined))
{i=true;}
if((o&&i))
{return class_object._shared.all}
else if(((!o)&&i))
{return class_object._shared.inherited}
else if((o&&(!i)))
{return class_object._shared.own}
else if(true)
{return{}}};class_object.listProperties=function(o,i){if((o===undefined))
{o=true;}
if((i===undefined))
{i=true;}
if((o&&i))
{return class_object._properties.all}
else if(((!o)&&i))
{return class_object._properties.inherited}
else if((o&&(!i)))
{return class_object._properties.own}
else if(true)
{return{}}};class_object.proxyWithState=function(o){var proxy={};var constr=undefined;var wrapper=function(f){return function(){return f.apply(o,arguments)}};var proxy_object=function(){return class_object.prototype.initialize.apply(o,arguments)};proxy_object.prototype=proxy;for(var key in class_object.prototype){var w=wrapper(class_object.prototype[key])
if(key=="initialize"){constr=w}
proxy[key]=w
proxy_object[key]=w}
proxy_object.getSuper=function(){return class_object.getParent().proxyWithState(o)};return proxy_object};if(declaration.parent!=undefined){for(var name in declaration.parent._operations.fullname){var operation=declaration.parent._operations.fullname[name]
class_object._operations.fullname[name]=operation
class_object[name]=operation}
for(var name in declaration.parent._operations.all){var operation=declaration.parent[name]
class_object[name]=operation
class_object._operations.all[name]=operation
class_object._operations.inherited[name]=operation}
for(var name in declaration.parent._methods.all){var method=declaration.parent._methods.all[name]
class_object._methods.all[name]=method
class_object._methods.inherited[name]=method}
for(var name in declaration.parent._shared.all){var attribute=declaration.parent._shared.all[name]
class_object[name]=attribute
class_object._shared.all[name]=attribute
class_object._shared.inherited[name]=attribute}
for(var name in declaration.parent._properties.all){var prop=declaration.parent._properties.all[name]
class_object._properties.all[name]=prop
class_object._properties.inherited[name]=prop}}
if(declaration.operations!=undefined){for(var name in declaration.operations){var operation=declaration.operations[name]
class_object[name]=operation
class_object[full_name+"_"+name]=operation
class_object._operations.all[name]=operation
class_object._operations.all[name]=operation
class_object._operations.own[name]=operation
class_object._operations.fullname[full_name+"_"+name]=operation}}
if(declaration.methods!=undefined){for(var name in declaration.methods){var method=declaration.methods[name]
class_object._methods.all[name]=method
class_object._methods.own[name]=method}}
if(declaration.shared!=undefined){for(var name in declaration.shared){var attribute=declaration.shared[name]
class_object[name]=attribute
class_object._shared.all[name]=attribute
class_object._shared.own[name]=attribute}}
if(declaration.properties!=undefined){for(var name in declaration.properties){var attribute=declaration.properties[name]
class_object._properties.all[name]=attribute
class_object._properties.own[name]=attribute}}
var instance_proto={};if(declaration.parent)
{instance_proto=new declaration.parent('__Extend_SubClass__');instance_proto.constructor=class_object;}
instance_proto.isInstance=undefined;instance_proto.getClass=function(){return class_object};instance_proto.isClass=function(){return false};instance_proto.getMethod=function(methodName){var this_object=this;return class_object.bindMethod(this_object,methodName)};instance_proto.getCallback=function(methodName){var this_object=this;return class_object.bindCallback(this_object,methodName)};instance_proto.isInstance=function(c){return c.hasInstance(this)};if(declaration.initialize)
{instance_proto.initialize=declaration.initialize;}
else if(true)
{instance_proto.instance_proto={};}
instance_proto.getSuper=function(c){return c.proxyWithState(this)};if(declaration.operations!=undefined){for(var name in declaration.operations){instance_proto[name]=instance_proto[full_name+"_"+name]=class_object.getOperation(name)}}
if(declaration.methods!=undefined){for(var name in declaration.methods){instance_proto[name]=instance_proto[full_name+"_"+name]=declaration.methods[name]}}
if(declaration.initialize!=undefined){instance_proto.initialize=instance_proto[full_name+"_initialize"]=declaration.initialize}
class_object.prototype=instance_proto;if(declaration.name)
{if((extend.Registry!=undefined))
{extend.Registry[declaration.name]=class_object;}}
return class_object}
extend.Protocol=function(pdata){var __this__=extend;}
extend.Singleton=function(sdata){var __this__=extend;}
extend.ErrorCallback=undefined
extend.PrintCallback=undefined
extend.invoke=function(t,f,args,extra){var __this__=extend;var meta=f['__meta__'];var actual_args=[];extend.iterate(extra['*'],function(v){args.push(v)},__this__)
extend.iterate(extra['**'],function(v,k){extra[k]=v;},__this__)
extend.iterate(args,function(v){actual_args.push(args)},__this__)
var start=args.length;while((start<meta.arity))
{var arg=meta.arguments[start];actual_args.push(extra[arg.name])
start=(start+1);}
return f.apply(t,actual_args)}
extend.range=function(start,end,step){var __this__=extend;var result=[];if(start<end){for(var i=start;i<end;i++){result.push(i);}}
else if(start>end){for(var i=start;i>end;i--){result.push(i);}}
return result}
extend.iterate=function(value,callback,context){var __this__=extend;if(!value){return}
if(value.length!=undefined){var length=undefined
if(typeof(value.length)=="function"){length=value.length()
for(var i=0;i<length;i++){var cont=callback.call(context,value.get(i),i)
if(cont==false){i=length+1};}}else{length=value.length
for(var i=0;i<length;i++){var cont=callback.call(context,value[i],i);if(cont==false){i=length+1};}}}else{for(var k in value){var cont=callback.call(context,value[k],k);if(cont==false){i=length+1};}}}
extend.sliceArguments=function(args,index){var __this__=extend;var res=[];while(index<args.length){res.push(args[index++])}
return res}
extend.slice=function(value,start,end){var __this__=extend;start=start===undefined?0:start
end=end===undefined?undefined:end
if(extend.isString(value))
{if((end===undefined))
{end=value.length;}
if((start<0))
{start=(value.length+start);}
if((end<0))
{end=(value.length+end);}
return value.substring(start,end)}
else if(extend.isList(value))
{if((end===undefined))
{end=value.length;}
if((start<0))
{start=(value.length+start);}
if((end<0))
{end=(value.length+end);}
return value.slice(start,end)}
else if(true)
{throw('Unsupported type for slice:'+value)}}
extend.isIn=function(value,list){var __this__=extend;if(extend.isList(list))
{for(var i=0;i<list.length;i++){if(list[i]==value){return true}}
return false}
else if(extend.isMap(list))
{for(var i in list){if(list[i]==value){return true}}
return false}
else if(true)
{return false}}
extend.createMapFromItems=function(items){var __this__=extend;items=extend.sliceArguments(arguments,0)
var result={}
for(var i=0;i<items.length;i++){result[items[i][0]]=items[i][1]}
return result}
extend.isDefined=function(value){var __this__=extend;return(!(value===undefined))}
extend.isList=function(value){var __this__=extend;return!!(!(value===null)&&typeof value=="object"&&value.join&&value.splice);}
extend.isString=function(value){var __this__=extend;return(typeof(value)=='string')}
extend.isMap=function(value){var __this__=extend;return!!(!(value===null)&&typeof value=="object"&&!extend.isList(value))}
extend.isFunction=function(value){var __this__=extend;return!!(typeof value=="function")}
extend.isInstance=function(value,ofClass){var __this__=extend;ofClass=ofClass===undefined?undefined:ofClass
if(ofClass)
{return(extend.isDefined(value.getClass)&&value.isInstance(ofClass))}
else if(true)
{return extend.isDefined(value.getClass)}}
extend.getMethodOf=function(instance,name){var __this__=extend;return instance[name]}
extend.getClassOf=function(instance){var __this__=extend;return instance.getClass()}
extend.print=function(args){var __this__=extend;args=extend.sliceArguments(arguments,0)
var pr_func=eval('print');if((((typeof(console)=='undefined')&&(typeof(pr_func)==='undefined'))&&(extend.PrintCallback===undefined)))
{return null}
var res='';for(var i=0;i<args.length;i++){var val=args[i]
if(val!=undefined&&typeof(val)=="object"&&val.toSource!=undefined){val=val.toSource()}
if(i<args.length-1){res+=val+" "}
else{res+=val}}
if((extend.PrintCallback===undefined))
{if((typeof(console)!='undefined'))
{console.log(res)}
else if(((typeof(document)=='undefined')&&(typeof(pr_func)!='undefined')))
{pr_func(res)}}
else if(true)
{extend.PrintCallback(res)}}
extend.error=function(message){var __this__=extend;if(extend.ErrorCallback)
{extend.ErrorCallback(message)}
else if(true)
{extend.print(('[!] '+message))}}
extend.assert=function(predicate,message){var __this__=extend;if((!predicate))
{extend.error(message)}}
extend.Registry={}
extend.getClass=function(name){var __this__=extend;return extend.Registry[name]}
extend.getParentClass=function(object){var __this__=extend;return extend.Registry[name]}
extend.getClasses=function(){var __this__=extend;return extend.Registry}
extend.getMethod=function(name,object){var __this__=extend;}
extend.getSuperMethod=function(name,object){var __this__=extend;}
extend.getChildrenOf=function(aClass){var __this__=extend;var res={};var values=extend.getClasses()
for(key in values){if(values[key]!=aClass&&values[key].isSubclassOf(aClass))
{res[key]=values[key]}}
return res}
extend.car=function(list){var __this__=extend;}
extend.cdr=function(list){var __this__=extend;}
extend.cons=function(list){var __this__=extend;}
extend.len=function(value){var __this__=extend;if(extend.isList(value))
{return value.length}
else if(isObject(value))
{if(value.length)
{return value.length}
else if(value.__len__)
{return value.__len__()}}
else if(true)
{return null}}
extend.map=function(callback,iterable){var __this__=extend;}
extend.filter=function(callback,iterable){var __this__=extend;}
extend.reduce=function(callback,iterable){var __this__=extend;}
extend.init=function(){var __this__=extend;String.__len__=function(){return this.length};Array.extend=function(array){};Array.append=function(){};Array.insert=function(){};Array.slice=function(){};Array.__iter__=function(){return this.length};Array.__len__=function(){return this.length};Object.keys=function(){};Object.items=function(){};Object.values=function(){};Object.hasKey=function(key){};Object.get=function(key){};Object.set=function(key,value){};Object.setDefault=function(key,value){};Object.__iter__=function(){};Object.__len__=function(){};}
extend.init()