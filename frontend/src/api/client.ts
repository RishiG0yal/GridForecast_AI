import axios from 'axios';

const client = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.response.use(
  (r) => r,
  (e) => {
    console.error('API Error:', e.response?.data || e.message);
    return Promise.reject(e);
  }
);

export default client;
