






function toarray(string) {
    var result = [];

    for (let i = 0; i < string.length; i++) {
        result.push(string.charCodeAt(i))
    };
    return result
};

var array = toarray('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36');
console.log(array);
