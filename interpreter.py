import sys
import types
import esprima
from js_properties import Prototype
from environment import init_globalEnv, ExecutionContext, Environment

userfunc_tostring = {}


def unsigned_right_shift(x, n):
    return (x & 0xFFFFFFFF) >> n

def signed_32bit2(left, right):
    v = (left << right) & 0xFFFFFFFF
    if v & 0x80000000:
        v -= 0x100000000
    return v

def bitwise_left_shift(val, shift):
    val = val & 0xFFFFFFFF
    val = (val << shift) & 0xFFFFFFFF
    if val >= 0x80000000:
        val -= 0x100000000
    return val

def xor_32(left, right):
    a_32 = left & 0xFFFFFFFF
    b_32 = right & 0xFFFFFFFF
    v = (a_32 ^ b_32) & 0xFFFFFFFF
    if v & 0x80000000:
        v -= 0x100000000
    return v


def signed_right_shift(val, shift):
    val = val & 0xFFFFFFFF
    if val & 0x80000000:
        val = val - 0x100000000
    return val >> shift

def js_in_operator(left, right):
    if isinstance(right, dict):
        return str(left) in right
    elif isinstance(right, list):
        try:
            index = int(left)
        except ValueError:
            return False
        return 0 <= index < len(right)
    else:
        raise TypeError(f"Cannot use 'in' operator with {type(right)}")
    
def ast_to_dict(node):
    if isinstance(node, list):
        return [ast_to_dict(n) for n in node]
    elif hasattr(node, '__dict__'):
        return {key: ast_to_dict(value) for key, value in node.__dict__.items()}
    else:
        return node
    
Function = {
    'bind': lambda fn, this_arg: lambda *args: lambda *more_args: fn(this_arg, *(args + more_args)),
    'call': lambda fn, this_arg, *args: fn(this_arg, *args),
    'apply': lambda fn, this_arg, arg_list: fn(this_arg, *arg_list),
    'toString': lambda fn: 'function() { [native code] }'
}

class JSFunction:
    __name__ = 'JSFunction'
    def __init__(self, constructor_func, new_target=False):
        self.func = constructor_func
        self.props = {}
        self.prototype = {'constructor': self}
        self.prototype.update(Function)
        self.new_target = new_target

    def instantiate(self, *args):
        instance = {}
        self.constructor_func(*args, new_target=True, this=instance)
        for name, method in self.prototype.items():
            if callable(method):
                instance[name] = method.__get__(instance)
            else:
                instance[name] = method
        return instance
    
    def __call__(self, *args, new_target=None, this=None):
        if new_target:
            this =self.prototype
        if isinstance(self.func, types.LambdaType):
            return self.func(*args, this=this)
        return self.func(*args, new_target=new_target, this=this)
    
    def __getitem__(self, key):
        if key == 'prototype':
            return self.prototype
        if key in self.props:
            return self.props[key]
        if key in self.prototype:
            prop = self.prototype[key]
            
            if callable(prop):
                return lambda *args, **kwargs: prop(self.func, *args, **kwargs)
            return prop
        raise KeyError('Unknown property:', key)

    def __setitem__(self, key, value):
        if key == 'prototype':
            self.prototype = value
        else:
            self.props[key] = value

class JSInterpreter:
    def __init__(self, code, exec_ctx):
        self.scriptCode = code
        self.call_stack = [exec_ctx]
        self.flags = {
            'continue': False,
            'break': False
        }
        
    def evaluate(self, node, ctx=None):
        if ctx is None:
            ctx = self.call_stack[len(self.call_stack) - 1]
            
        if node['type'] == 'Program':
            self.hoistVariables(node, ctx)
            result = None
            for nodo in node['body']:
                evaluated = self.evaluate(nodo)
                
                if evaluated is not None:
                    result = evaluated
            return result
        
        if node['type'] == 'FunctionDeclaration':
            self_ref = self
            parent_env = ctx.env
            is_new_target = False

            def func(*args, new_target=None, this=None):
                nonlocal is_new_target
                
                activation_record = {}
                for i in range(len(node['params'])):
                    param_name = node['params'][i]['name']
                    activation_record[param_name] = args[i] if i < len(args) else None

                activation_record['arguments'] = list(args)

                if new_target:
                    is_new_target = True
                    this = this or {}
                    for stmt in node['body']['body']:
                        result = self_ref.constructor_props(stmt, ctx)
                        if result:
                            this.update(result)
                            
                if this is None:
                    this = {}
                    
                    
                this['constructor'] = func

                env_inner = Environment(activation_record, parent_env)
                exec_ctx = ExecutionContext(this, env_inner)
                self_ref.call_stack.append(exec_ctx)

                result = self_ref.eval_function_block(node['body'], exec_ctx)

                if new_target:
                    return this
                return result
            
            func = JSFunction(func, is_new_target)

            ctx.env.define(node['id']['name'], func)
            ctx.env.define(f"{node['id']['name']}__class", func)
            return
        
        if node['type'] == 'NewExpression':
            callee = self.evaluate(node['callee'], ctx)
            
            args = [self.evaluate(arg, ctx) for arg in node['arguments']]
            if isinstance(callee, JSFunction) and hasattr(callee, '__name__'):
                result = callee(*args, new_target=True)
            if callee.__name__ == 'func':
                result = callee(*args, new_target=True)
            else:
                result = callee(*args)
            return result
        
        if node['type'] == 'ContinueStatement':
            self.flags['continue'] = True
            return
        
        if node['type'] == 'BreakStatement':
            self.flags['break'] = True
            return
        
        if node['type'] == 'ThrowStatement':
            raise self.evaluate(node['argument'], ctx)
        
        if node['type'] == 'TryStatement':
            result = None
            
            try:
                result = self.evaluate(node['block'], ctx)
            except Exception as e:
                param_name = node['handler']['param']['name']
                ctx.env.define(param_name, e)
                result = self.evaluate(node['handler']['body'], ctx)
                
            if node['finalizer']:
                return self.evaluate(node['finalizer'], ctx)
            return result
        
        if node['type'] == 'FunctionExpression':
            if node['id']:
                name = node['id']['name']
            else:
                name = None

            this = self
            parent_env = ctx.env
            is_new_target = False

            def func(*args, new_target=None, this={}):
                nonlocal is_new_target
                activation_record = {}
                
                if new_target:
                    is_new_target = True

                if name:
                    activation_record[name] = func

                for i in range(len(node['params'])):
                    param = node['params'][i]['name']
                    activation_record[param] = args[i] if i < len(args) else None

                activation_record['arguments'] = list(args)
                
                this = this or {}
                this['constructor'] = func

                env_inner = Environment(activation_record, parent_env)
                exec_ctx = ExecutionContext(this or {}, env_inner)
                self.call_stack.append(exec_ctx)
                
                result = self.eval_function_block(node['body'], exec_ctx)
                return result
            
            func = JSFunction(func, is_new_target)
            func['call'] = lambda this, *args: func(*args, this=this)
            return func
        
        if node['type'] == 'ReturnStatement':
            function_result = None
            
            if node['argument'] is not None:
                function_result = self.evaluate(node['argument'], ctx)
                
            self.call_stack.pop()
            return function_result
        
        if node['type'] == 'ExpressionStatement':
            return self.evaluate(node['expression'])
        
        if node['type'] == 'Literal' and 'value' in node:
            if 'regex' in node:
                pattern = node['regex']['pattern']
                flags = node['regex']['flags']
                return ctx.selfValue['RegExp'](pattern, flags)
            return node['value']
        
        if node['type'] == 'UnaryExpression':
            argument, prop = self.resolve_unary_expression(node['argument'], ctx)
            if not argument:
                argument = self.evaluate(node['argument'])

            if node['operator'] == '!':
                return not argument
            elif node['operator'] == '-':
                return -argument
            elif node['operator'] == '+':
                return +argument
            elif node['operator'] == '~':
                return ~argument
            elif node['operator'] == 'typeof':
                return type(argument)
            elif node['operator'] == 'void':
                return None
            elif node['operator'] == 'delete':
                del argument[prop]
                return
            else:
                raise TypeError('unknown unary operator:', node['operator'])
                
        if node['type'] == 'LogicalExpression':
            left = self.evaluate(node['left'])
            right = self.evaluate(node['right'])
            
            if node['operator'] == '||':
                return left or right
            elif node['operator'] == '&&':
                return left and right
            elif node['operator'] == '??':
                return left if left is not None else right
            else:
                raise TypeError('unknown logical operator:', node['operator'])
        
        if node['type'] == 'BinaryExpression':
            left = self.evaluate(node['left'])
            right = self.evaluate(node['right'])
            
            if isinstance(left, float):
                left = int(left)
            if isinstance(right, float):
                right = int(right)
                
            if isinstance(right, types.LambdaType):
                right = right()
            if isinstance(left, types.LambdaType):
                left = left()
                
            if left == None and isinstance(right, int):
                return False
            
            if node['operator'] == '+':
                return left + right
            elif node['operator'] == '-':
                return left - right
            elif node['operator'] == '*':
                return left * right
            elif node['operator'] == '/':
                return left / right
            elif node['operator'] == '%':
                return left % right
            elif node['operator'] == '**':
                return left ** right
            elif node['operator'] == '==':
                return left == right
            elif node['operator'] == '===':
                return left == right
            elif node['operator'] == '!=':
                return left != right
            elif node['operator'] == '!==':
                return left != right
            elif node['operator'] == '<':
                return left < right
            elif node['operator'] == '<=':
                return left <= right
            elif node['operator'] == '>':
                return left > right
            elif node['operator'] == '>=':
                return left >= right
            elif node['operator'] == '|':
                return left | right
            elif node['operator'] == '&':
                return left & right
            elif node['operator'] == '^':
                return xor_32(left, right)
            elif node['operator'] == '<<':
                return signed_32bit2(left, right)
            elif node['operator'] == '>>':
                return left >> right
            elif node['operator'] == '>>':
                return left >> right
            #elif node['operator'] == '>>>':
            #    return unsigned_right_shift(left, right)
            elif node['operator'] == 'in':
                return js_in_operator(left, right)
            elif node['operator'] == 'instanceof':
                return isinstance(left, right)
            else:
                raise TypeError('unknown operator:', node['operator'])
                
        if node['type'] == 'VariableDeclaration':
            result = None
            
            for declarator in node['declarations']:
                evaluated = self.evaluate(declarator, ctx)

                if evaluated is not None:
                    result = evaluated
            return result
                
        if node['type'] == 'VariableDeclarator':
            name = node['id']['name']
            if not node['init']:
                return
            value = self.evaluate(node['init'], ctx)
            
            return ctx.env.define(name, value)
        
        if node['type'] == 'Identifier':
            return ctx.env.lookup(node['name'])
        
        if node['type'] == 'AssignmentExpression':
            if node['left']['type'] == 'Identifier':
                left = node['left']['name']
                right = self.evaluate(node['right'], ctx)
                prevValue = self.evaluate(node['left'], ctx)
                
                if node['operator'] == '=':
                    return ctx.env.assign(left, right)
                elif node['operator'] == '+=':
                    return ctx.env.assign(left, prevValue + right)
                elif node['operator'] == '-=':
                    return ctx.env.assign(left, prevValue - right)
                elif node['operator'] == '*=':
                    return ctx.env.assign(left, prevValue * right)
                elif node['operator'] == '/=':
                    return ctx.env.assign(left, prevValue / right)
                elif node['operator'] == '^=':
                    return ctx.env.assign(left, xor_32(prevValue, right))
                elif node['operator'] == '&=':
                    return ctx.env.assign(left, prevValue & right)
                elif node['operator'] == '|=':
                    return ctx.env.assign(left, prevValue | right)
                elif node['operator'] == '<<=':
                    return ctx.env.assign(left, bitwise_left_shift(prevValue, right))
                elif node['operator'] == '>>=':
                    return ctx.env.assign(left, signed_right_shift(prevValue, right))
                elif node['operator'] == '%=':
                    return ctx.env.assign(left, prevValue % right)
                else:
                    raise TypeError('Unknown operator assignment:', node['operator'])
                
            if node['left']['type'] == 'MemberExpression':
                obj, prop = self.resolve_member_target(node['left'], ctx)
                prop_value = self.evaluate(node['right'], ctx)
                
                if obj is None:
                    pass
                
                obj = Prototype.object_properties2(obj)

                operator = node['operator']
                if operator == '=':
                    if isinstance(prop, list):
                        prop = ''
                    #print('LOOK', obj, prop, prop_value, type(prop))
                    obj[prop] = prop_value
                    return obj[prop]
                
                prev_value = obj.get(prop, None)
                if prev_value is None:
                    raise TypeError(f"Property '{prop}' not found in object")
                
                if node['operator'] == '=':
                    obj[prop] = prop_value
                    return obj[prop]
                elif node['operator'] == '+=':
                    obj[prop] = prev_value + prop_value
                    return obj[prop]
                elif node['operator'] == '<<=':
                    return bitwise_left_shift(left, right)
                elif node['operator'] == '-=':
                    obj[prop] = prev_value - prop_value
                    return obj[prop]
                elif node['operator'] == '*=':
                    obj[prop] = prev_value * prop_value
                    return obj[prop]
                elif node['operator'] == '/=':
                    obj[prop] = prev_value / prop_value
                    return obj[prop]
                elif node['operator'] == '^=':
                    return ctx.env.assign(left, xor_32(prev_value, prop_value))
                else:
                    raise TypeError('Unknown operator assignment:', node['operator'])
            raise TypeError('Unknown assignment for node type:', node['left']['type'])
                
        if node['type'] == 'UpdateExpression':
            if node['argument']['type'] == 'Identifier':
                var_name = node['argument']['name']
                var_value = self.evaluate(node['argument'], ctx)
                
                new_value = var_value + 1 if node['operator'] == '++' else var_value - 1
                
                if node['prefix']:
                    return ctx.env.assign(var_name, new_value)
                
                ctx.env.assign(var_name, new_value)
                return var_value
            
            if node['argument']['type'] == 'MemberExpression':
                obj_env = self.evaluate(node['argument']['object'], ctx)
                if node['argument']['computed']:
                    prop = self.evaluate(node['argument']['property'], ctx)
                else:
                    prop = node['argument']['property']['name']
                    
                prop_value = obj_env[prop]
                new_value = prop_value + 1 if node['operator'] == '++' else prop_value - 1
                
                if node['prefix']:
                    obj_env[prop] = new_value
                    return obj_env[prop]
                
                obj_env[prop] = new_value
                return prop_value
                    
            
        if node['type'] == 'SequenceExpression':
            result = None
            
            expressions = node['expressions']
            
            for expr in expressions:
                evaluated = self.evaluate(expr, ctx)
                
                if evaluated is not None:
                    result = evaluated
            return result
        
        if node['type'] == 'ThisExpression':
            return ctx.selfValue
        
        if node['type'] == 'ObjectExpression':
            obj = {}
            for prop in node['properties']:
                key = prop['key'].get('name', None) or prop['key']['value']
                value = self.evaluate(prop['value'], ctx)
                
                obj[key] = value
            return obj
        
        if node['type'] == 'Literal':
            if node['type'] == 'NullLiteral':
                return None
            
            if node['type'] == 'RegExpLiteral':
                return ctx.selfValue.RegExp(node['pattern'], node['flags'])
            return node['value']
        
        if node['type'] == 'ArrayExpression':
            elements = [self.evaluate(el, ctx) for el in node['elements']]
            array = [value for value in elements]
            return array
        
        if node['type'] == 'ConditionalExpression':
            if self.evaluate(node['test'], ctx):
                return self.evaluate(node['consequent'], ctx)
            else:
                return self.evaluate(node['alternate'], ctx)
        
        if node['type'] == 'IfStatement':
            test = self.evaluate(node['test'], ctx)
            
            if test:
                return self.evaluate(node['consequent'], ctx)
            elif node['alternate'] != None:
                return self.evaluate(node['alternate'], ctx)
            else:
                return
        
        if node['type'] == 'BlockStatement':
            self.hoistVariables(node, ctx)
            result = None
            
            for stmt in node['body']:
                result = self.evaluate(stmt, ctx)
                
                if self.call_stack[len(self.call_stack) - 1] != ctx:
                    return result
                
                if self.flags['continue'] or self.flags['break']:
                    break
            return result
        
        if node['type'] == 'CallExpression':
            selfCtx = None
            callee_node = node['callee']
            
            if callee_node['type'] == 'MemberExpression':
                selfCtx = self.evaluate(callee_node['object'], ctx)
                
                if callee_node['computed']:
                    prop = self.evaluate(callee_node['property'], ctx)
                else:
                    prop = callee_node['property']['name']
                
                fn = self.evaluate(callee_node, ctx)
            else:
                fn = self.evaluate(callee_node, ctx)
                selfCtx = ctx.selfValue or None

            if not callable(fn):
                if fn is None:
                    print('function is not callable', fn, node)
                    return None
                raise TypeError('function is not callable', fn, node)
            
            args = [self.evaluate(arg, ctx) for arg in node['arguments']]

            if hasattr(fn, '__call__') and hasattr(fn, '__code__'):
                return fn(*args)
            elif isinstance(fn, JSFunction):
                return fn(*args, this=selfCtx)
            else:
                if fn == eval and args[0] is None:
                    return None
                return fn(*args)
        
        if node['type'] == 'MemberExpression':
            obj = self.evaluate(node['object'], ctx)
            
            if node['computed']:
                prop = self.evaluate(node['property'], ctx)
            else:
                prop = node['property']['name']
                
            if isinstance(obj, (dict, list, str)):
                obj, js_prop = Prototype.object_properties(obj, prop)
            else:
                js_prop = prop
            #print('MIRR', obj, js_prop, prop, type(obj))
            try:
                #print(js_prop in ctx.selfValue)
                if isinstance(obj, dict):
                    return obj.get(js_prop, None)
                else:
                    return obj[js_prop]
            except TypeError:
                return None
            #if prop in obj:
            #    return obj[prop]
            #elif obj is not None:
            #    return obj[prop]
            #elif '__proto__' in obj and not isinstance(obj, dict): # javascript,proxy.Proxy
            #    obj = obj['__proto__']
            
            #raise TypeError('Property not found in chain', prop, 'OBJ: ',obj)
        
        if node['type'] == 'WhileStatement':
            test = node['body']
            body = node['test']
            result = None
            
            while (self.call_stack[len(self.call_stack) - 1] == ctx and self.evaluate(test, ctx)):
                result = self.evaluate(body, ctx)
                
                if self.flags['continue']:
                    self.flags['continue'] = False
                if self.flags['break']:
                    self.flags['break'] = False
                    break
                
            return result
        
        if node['type'] == 'ForStatement':
            init = node['init']
            test = node['test']
            body = node['body']
            
            result = None
            
            if init:
                self.evaluate(init, ctx)
            
            while (self.call_stack[len(self.call_stack) - 1] == ctx and (self.evaluate(test, ctx) if test else 1)):
                result = self.evaluate(body, ctx)
                
                if self.flags['continue']:
                    self.flags['continue'] = False
                    
                if self.flags['break']:
                    self.flags['break'] = False
                    break
                
                if node['update']:
                    self.evaluate(node['update'], ctx)
            return result
        
        if node['type'] == 'DoWhileStatement':
            test = node['test']
            body = node['body']
            result = None
            
            while True:
                result =  self.evaluate(body, ctx)
                
                if self.flags['continue']:
                    self.flags['continue'] = False
                    
                if self.flags['break']:
                    self.flags['break'] = False
                    break
                
                if self.call_stack[-1] != ctx:
                    break
                
                if not self.evaluate(test, ctx):
                    break
            return result
        
        if node['type'] == 'ForInStatement':
            obj = self.evaluate(node['right'], ctx)
            var_name = node['left']['declarations'][0]['id']['name']
            
            for key in obj:
                ctx.env.define(var_name, key)
                self.evaluate(node['body'], ctx)
            return
        
        if node['type'] == 'SwitchStatement':
            test = self.evaluate(node['discriminant'], ctx)
            result = None
            
            for i in range(len(node['cases'])):
                case_clause = node['cases'][i]
                
                if case_clause['test'] != None and self.evaluate(case_clause['test'], ctx) == ctx:
                    result = self.eval_case_clause(case_clause, ctx)
                    
                    if self.flags['break'] == True:
                        self.flags['break'] = False
                    break
                elif case_clause['test'] == None:
                    result = result = self.eval_case_clause(case_clause, ctx)
                    if self.flags['break'] == True:
                        self.flags['break'] = False
            return result
            
        if node['type'] == 'EmptyStatement':
            return
        
        raise TypeError('Unknown Node Instruction:', node)
    
    def hoistVariables(self, block, ctx):
        for stmt in block['body']:
            if stmt['type'] == 'FunctionDeclaration':
                self.evaluate(stmt, ctx)
                
            if stmt['type'] == 'VariableDeclaration':
                for declarator in stmt['declarations']:
                    name = declarator['id']['name']
                    ctx.env.define(name, None)
                    
    def constructor_props(self, block, ctx):
        obj = {}
        
        if block['type'] == 'ExpressionStatement':
            prop = block['expression']['left']['property']['name']
            var_value = self.evaluate(block, ctx)
            obj[prop] = var_value
        return obj
                    
    def eval_case_clause(self, case_clause, ctx):
        result = None
        
        for i in range(len(case_clause['consequent'])):
            stmt = case_clause['consequent'][i]
            result = self.evaluate(stmt, ctx)
            
            if self.call_stack[len(self.call_stack) - 1] != ctx:
                if self.flags['break'] == True:
                    self.flags['break'] == False
                return result
        return result
    
    def resolve_member_target(self, node, ctx):
        obj_name = node['object'].get('name', None)
        
        if node['type'] != 'MemberExpression':
            raise TypeError("Expected MemberExpression")

        if node['object']['type'] == 'MemberExpression':
            parent_obj, parent_prop = self.resolve_member_target(node['object'], ctx)
            obj = parent_obj[parent_prop]
        else:
            obj = self.evaluate(node['object'], ctx)
            
        if obj_name is None and obj is None:
            oe = self.evaluate(node['object'], ctx)

        if node['computed']:
            prop = self.evaluate(node['property'], ctx)
        else:
            prop = node['property']['name']
            
        return obj, prop
    
    def resolve_unary_expression(self, node, ctx):
        if node['type'] == 'MemberExpression':
            if node['computed'] and 'object' in node and 'property' in node:
                obj_name = node['object']['name']
                prop = node['property']['name']
                obj = ctx.env.lookup(obj_name)
                prop_value = ctx.env.lookup(prop)
                return obj, prop_value
        return False, None
    
    def is_constructor_func(self, node):
        for body in node['body']:
            print(body)
            
        sys.exit()
     
    def eval_function_block(self, block, ctx):
        self.hoistVariables(block, ctx)
        result = None
        
        for s in range(len(block['body'])):
            stmt = block['body'][s]
            
            result = self.evaluate(stmt, ctx)
            
            if self.call_stack[len(self.call_stack) - 1] != ctx:
                return result
        
        self.call_stack.pop()
        return result
    
    @staticmethod
    def parse_code(code):
        sys.setrecursionlimit(5000)
        return ast_to_dict(esprima.parseScript(code))

if __name__ == '__main__':
    sys.setrecursionlimit(5000)
    code = open('tests/test13.js', 'r').read()
    
    ctx = init_globalEnv(
        domain='https://nopecha.com/demo/cloudflare',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        html=open('tests/html_test.html', 'r').read()
    )
    interpreter = JSInterpreter(code, exec_ctx=ctx)
    interpreter.evaluate(interpreter.parse_code(code))
    result = interpreter.evaluate(interpreter.parse_code('show()'))
    
    print('Result', result)