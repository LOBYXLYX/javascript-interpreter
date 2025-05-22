import re
import sys
import types
from pyjsparser import parse
from environment import init_globalEnv, ExecutionContext, Environment

userfunc_tostring = {}

import ctypes

kernel32 = ctypes.windll.kernel32
handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
mode = ctypes.c_ulong()
kernel32.GetConsoleMode(handle, ctypes.byref(mode))
kernel32.SetConsoleMode(handle, mode.value | 0x0004)

def unsigned_right_shift(x, n):
    return (x & 0xFFFFFFFF) >> n

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
            this = self
            parent_env = ctx.env
            
            def func(*args, new_target=None, this=None):
                activation_record = {}
                
                for i in range(len(node['params'])):
                    
                    activation_record[node['params'][i]['name']] = list(args)[i]
                
                activation_record['arguments'] = [arg for arg in list(args)]
                
                if new_target:
                    this = {}
                    
                    for stmt in node['body']['body']:
                        sresult = self.constructor_props(stmt, ctx)
                        this.update(sresult)
                
                env_inner = Environment(activation_record, parent_env)
                exec_ctx = ExecutionContext(
                    this,
                    env_inner
                )
                
                self.call_stack.append(exec_ctx)
                
                if new_target:
                    self.eval_function_block(node['body'], exec_ctx)
                    return this
                
                result = self.eval_function_block(node['body'], exec_ctx)
                return result
            
            ctx.env.define(node['id']['name'], func)
            return
        
        if node['type'] == 'NewExpression':
            callee = self.evaluate(node['callee'], ctx)
            
            args = [self.evaluate(arg, ctx) for arg in node['arguments']]
            
            if not isinstance(callee, types.FunctionType):
                result = callee(*args)
            else:
                result = callee(*args, new_target=True)
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
            
            def func(*args, new_target=None, this={}):
                activation_record = {}
                
                if name:
                    activation_record[name] = func
                
                for i in range(len(node['params'])):
                    activation_record[node['params'][i]['name']] = list(args[i])
                
                activation_record['arguments'] = [arg for arg in list(args)]
                
                if new_target:
                    for stmt in node['body']['body']:
                        sresult = self.constructor_props(stmt, ctx)
                        this.update(sresult)
                
                env_inner = Environment(activation_record, parent_env)
                exec_ctx = ExecutionContext(
                    this,
                    env_inner
                )
                
                self.call_stack.append(exec_ctx)
                
                if new_target is not None:
                    self.eval_function_block(node['body'], exec_ctx)
                    return this
                
                result = self.eval_function_block(node['body'], exec_ctx)
                return result
            
            #func_string = self.scriptCode[int(node['loc']['start']['column']):int(node['loc']['end']['column'])]
            #userfunc_tostring[func] = func_string
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
            return node['value']
        
        if node['type'] == 'UnaryExpression':
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
            
            if node['operator'] == '+':
                return left + right
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
                return left ^ right
            elif node['operator'] == '<<':
                return left << right
            elif node['operator'] == '>>':
                return left >> right
            elif node['operator'] == '>>':
                return left >> right
            elif node['operator'] == '>>>':
                return unsigned_right_shift(left, right)
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
                    return ctx.env.assign(left, prevValue ^ right)
                elif node['operator'] == '&=':
                    return ctx.env.assign(left, prevValue & right)
                elif node['operator'] == '|=':
                    return ctx.env.assign(left, prevValue | right)
                elif node['operator'] == '%=':
                    return ctx.env.assign(left, prevValue % right)
                else:
                    raise TypeError('Unknown operator assignment:', node['operator'])
                
            if node['left']['type'] == 'MemberExpression':
                obj_name = node['left']['object'].get('name', None)
                obj = None
                
                if obj_name is None:
                    obj = self.evaluate(node['left']['object'], ctx)
                else:
                    obj = ctx.env.lookup(obj_name)
                
                if not obj and obj != {}:
                    raise TypeError('Undefined object in assignment...', node)
                
                prop = None
                
                if node['left']['computed']:
                    prop = self.evaluate(node['left']['property'], ctx)
                else:
                    prop = node['left']['property']['name']
                
                if prop is None:
                    raise TypeError('Undefined property in assignment...', node)
                if prop not in obj:
                    return 'XD1'
                
                prop_value = self.evaluate(node['right'], ctx)
                prev_value = obj[prop]
                
                if node['operator'] == '=':
                    obj[prop] = prop_value
                    return obj[prop]
                elif node['operator'] == '+=':
                    obj[prop] = prev_value + prop_value
                    return obj[prop]
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
                    return ctx.env.assign(left, prev_value ^ prop_value)
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
                key = prop['key']['name'] or prop['key']['value']
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
            fn = self.evaluate(node['callee'], ctx)
            
            if node['callee']['type'] == 'MemberExpression':
                selfCtx = self.evaluate(node['callee']['object'], ctx)
                
                if node['callee']['computed']:
                    prop = self.evaluate(node['callee']['property'], ctx)
                else:
                    prop = node['callee']['property']['name']
                fn = selfCtx[prop]
            else:
                fn = self.evaluate(node['callee'], ctx)
                selfCtx = ctx.selfValue
                
            if not fn:
                raise TypeError('function is not defined', node)                
            
            args = [self.evaluate(arg, ctx) for arg in node['arguments']]
            
            return fn(*args)
        
        if node['type'] == 'MemberExpression':
            obj = self.evaluate(node['object'], ctx)
            prop = None
            
            if node['computed']:
                prop = self.evaluate(node['property'], ctx)
            else:
                prop = node['property']['name']
            return obj[prop]
        
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
        
        raise TypeError('DJKCwegijgew')
    
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

if __name__ == '__main__':
    code = open('test2.js', 'r').read()
    
    ctx = init_globalEnv(
        domain='https://www.example.com',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    )
    interpreter = JSInterpreter(code, exec_ctx=ctx)
    result = interpreter.evaluate(parse(code))