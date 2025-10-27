import compression from 'compression';
import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;
const userServiceUrl = process.env.USER_SERVICE_URL || 'http://user-service:8000';
const taskServiceUrl = process.env.TASK_SERVICE_URL || 'http://task-service:8000';
const authUsername = process.env.FRONTEND_AUTH_USERNAME || process.env.AUTH_USERNAME || 'admin';
const authPassword = process.env.FRONTEND_AUTH_PASSWORD || process.env.AUTH_PASSWORD || 'changeme';
const apiAuthToken = process.env.FRONTEND_API_AUTH_TOKEN || process.env.API_AUTH_TOKEN || '';

app.use(helmet({ contentSecurityPolicy: false }));
app.use(compression());
app.use(morgan('dev'));

app.post('/auth/login', express.json(), (req, res) => {
  const { username, password } = req.body ?? {};
  if (username !== authUsername || password !== authPassword) {
    return res.status(401).json({ detail: 'Invalid credentials' });
  }
  if (!apiAuthToken) {
    return res.status(500).json({ detail: 'API authentication token is not configured' });
  }
  return res.json({ token: apiAuthToken });
});

app.use(
  '/users',
  createProxyMiddleware({
    target: userServiceUrl,
    changeOrigin: true,
    logLevel: 'warn',
  }),
);
app.use(
  '/tasks',
  createProxyMiddleware({
    target: taskServiceUrl,
    changeOrigin: true,
    logLevel: 'warn',
  }),
);

app.use(express.static(path.join(__dirname, 'public')));

app.get('/health', (_, res) => {
  res.json({ status: 'ok', service: 'frontend' });
});

app.listen(port, () => {
  console.log(`Frontend listening on port ${port}`);
});
