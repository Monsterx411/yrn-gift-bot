module.exports = {
  prettyFactory: function (opts) {
    return function (chunk, encoding, callback) {
      callback(null, chunk);
    };
  },
};
