function decryptArrHash(array, seed) {
    const static1 = 94906238;
    const static2 = 13558035;
    const static3 = 13037;

    const decrypted = new Array(array.length).fill(0);

    let byte0_1 = ((seed % static1) + static1) % static1;
    let byte0_2 = ((byte0_1 * static2) + static3) % static1;
    seed = byte0_2;
    decrypted[0] = (array[0] - byte0_2) % 256;

    for (let index = 1; index < array.length; index++) {
        let mod_1 = ((seed * static2) + static3) % static1;
        let mod_2 = mod_1 % static1;
        let original_byte = (array[index] - mod_2) % 256;
        decrypted[index] = original_byte;
        seed = mod_2;
    }

    return decrypted.map(function(c) {
        return String.fromCharCode(c);
    }).join('')
}

const a = decryptArrHash(
    [244, 39, 251, 233, 33, 14, 168, 81, 104, 42, 43, 80, 69, 25, 6, 28, 219, 229, 34, 11, 93, 102, 125, 18, 34, 86, 65, 232, 206, 196, 196, 213, 15, 196, 103, 73, 63, 96, 29, 80, 50, 206, 202, 10, 211, 206, 252, 219, 142, 102, 96, 71, 81, 65, 52, 215, 182, 190, 140, 142, 173, 162, 106, 66, 95, 33, 31, 52, 21, 6, 222, 241, 180, 110, 202, 213, 120, 91, 112, 243, 233, 65, 83, 2, 218, 233, 170, 115, 170, 153, 65, 20, 39, 238, 239, 34, 17, 166, 180, 211, 161, 155, 225, 197, 48, 17, 32, 237, 227, 29, 13],
    -552346152
);
console.log('result', a);
