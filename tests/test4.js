




var array = [];

for (let i = 0; i < 256; i++) {
    array.push(String.fromCharCode(i))
}

console.log(array)
var uint8 = new Uint8Array([2, 3, 4, 5])
console.log(uint8.byteLength)
uint8[0] = 211;
console.log(typeof uint8, uint8)

var decoder = new TextDecoder();

console.log(decoder.decode([2, 31, 43]))