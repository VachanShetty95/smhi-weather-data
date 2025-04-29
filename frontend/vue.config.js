module.exports = {
  devServer: {
    proxy: {
      '/': {
        target: 'http://backend:8000',
        changeOrigin: true
      }
    }
  }
} 