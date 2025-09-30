export const environment = {
  production: false,
  // apiUrl: 'http://localhost:5000/api/v1',
  // wsUrl: 'http://localhost:5000',
  apiUrl: 'https://demo-nhp-api.huce.edu.vn/api/v1',
  wsUrl: 'https://demo-nhp-api.huce.edu.vn',
  security: {
    enableLogging: true,
    tokenExpiry: 3600,
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000
  }
};
