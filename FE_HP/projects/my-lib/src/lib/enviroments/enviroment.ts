export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000/api/v1',
  security: {
    enableLogging: true,
    tokenExpiry: 3600,
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000
  },
  jwt: {
    secret: 'water-leak-dev-secret-key-2024-change-in-production',
    expiresIn: '1h',
    refreshExpiresIn: '7d',
    issuer: 'water-leak-system',
    audience: 'water-leak-client'
  }
};
