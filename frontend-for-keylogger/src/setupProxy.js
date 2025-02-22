const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api', // This is the key part:  Proxy requests starting with /api
    createProxyMiddleware({
      target: 'http://localhost:5000', // Your Flask backend
      changeOrigin: true,
      proxyTimeout: 60000
    })
  );
}; 