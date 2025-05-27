

function mul(x) {
    return 10 * x;
}

function cf() {
    this.A = 10;
}

cf.prototype.metodo = function () {
    console.log('HELLLO WORLD!');
}

cf.prototype.letsgo = function(x) {
    console.log(x)
}
var array = [];
var xc = new cf();
console.log(typeof cf, cf.prototype, 'SXD', xc.metodo(), xc.letsgo('VAMO'))
console.log(array.push);