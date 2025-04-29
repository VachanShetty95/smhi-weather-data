import { createApp } from 'vue'
import App from './App.vue'
import './assets/main.css'
import axios from 'axios'

// Configure axios
// When the application is running in a browser, requests should go through the current origin
// which will be handled by the Nginx proxy
console.log('Running with base URL:', window.location.origin);
axios.defaults.baseURL = window.location.origin;

// Additional axios configuration
axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
axios.defaults.timeout = 30000; // 30 seconds timeout

// Create and mount the app
createApp(App).mount('#app') 