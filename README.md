
# Features
Window API (Incompleted, there may be errors)

Fast

100% Python Based



# Examples: (in tests dir)
- test
```python
from interpreter import JSInterpreter
from environment import init_globalEnv

ctx = init_globalEnv(
    domain='https://www.example.com',
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    html=''
)

code = """
function mul(x) {
    return 10 * x;
};

var array = [];

for (let i = 0; i < 32; i++) {
    array.push(mul(i));
};

console.log(array);
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(interpreter.parse_code(code))
# [0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,310]
```


```python
# ...

code = """
var uint8 = Uint8Array(30)
uint[0] = 124

console.log(typeof uint8) // <class 'window.CreateArrayOfBytes'>
console.log(uint8.length) // 30
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(interpreter.parse_code(code))
```

```python
# ...

code = """
console.log(Object.getOwnPropertyNames(window))
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(interpreter.parse_code(code))
# ['chrome', 'clearInterval', 'clearTimeout', 'closed', 'clientInformation', 'crypto', 'atob', 'btoa', 'isSecureContext',.........
```

- using Window properties
```python
# ...

code = """
var ua = window.navigator.userAgent; // or var ua = navigator.userAgent
console.log(ua);
"""

interpreter = JSInterpreter(code, exec_ctx=ctx)
result = interpreter.evaluate(interpreter.parse_code(code))
# Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36
```


discord: lobyx1
