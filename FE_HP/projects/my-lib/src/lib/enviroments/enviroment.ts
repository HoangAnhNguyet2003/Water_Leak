export const environment = {
  production: false,
  // apiUrl: 'http://localhost:5000/api/v1',
  // wsUrl: 'http://localhost:5000',
  apiUrl: 'http://192.168.0.30:5000/api/v1',
  wsUrl: 'http://192.168.0.30:5000',
  security: {
    enableLogging: true,
    tokenExpiry: 3600,
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000
  }
};
