***Note: You can't define classes or prototypes, since it's done in Python, it's hard to interpret advanced code in Python***

# Examples:
- test
```python
from pyjsparser import parse
from interpreter import JSInterpreter
from environment import init_globalEnv, ExecutionContext, Environment

ctx = init_globalEnv(
    domain='https://www.example.com',
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
)

code = """
function mul(x) {
    return 10 * x;
}

var array = [];

for (let i = 0; i < 32; i++) {
    array.push(mul(i));
};

console.log(array);
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(parse(code))
# [0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,310]
```

- using Window properties
```python
# ...

code = """
var body = window.document.body;

console.log(body);
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(parse(code))
# HTMLBodyElement {}
```
