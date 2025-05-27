
#from sandbox.dom import Sandbox
import sys
from window import Window

class ExecutionContext:
    def __init__(self, selfValue, env):
        self.selfValue = selfValue
        self.env = env

class Environment:
    def __init__(self, record={}, parent=None):
        self.record = record
        self.parent = parent
        
    def define(self, name, value=None):
        self.record[name] = value
        return value
    
    def lookup(self, name):
        return self.resolve(name).record[name]
    
    def resolve(self, name):
        if name in self.record:
            return self
        
        if self.parent == None:
            raise TypeError(f'Variable "{name}" is not defined')
        
        return self.parent.resolve(name)
    
    def assign(self, name, value):
        self.resolve(name).record[name] = value
        return value
    
def init_globalEnv(**kwargs):
    sandbox = Window(**kwargs)
    globalenv = Environment(sandbox.env)
    globalexec = ExecutionContext(sandbox.env, globalenv)
    return globalexec