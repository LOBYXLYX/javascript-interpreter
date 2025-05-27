
const modulep = {
  x: 42,
  getX: function () {
    return this.x;
  },
};

const unboundGetX = modulep.getX;
console.log(unboundGetX()); // The function gets invoked at the global scope
// Expected output: undefined

const boundGetX = unboundGetX.bind(modulep);
console.log(boundGetX());
// Expected output: 42
