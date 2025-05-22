

function mul(x) {
    return 10 * x;
}

var array = [];

for (let i = 0; i < 32; i++) {
    array.push(mul(i));
};

console.log(array);