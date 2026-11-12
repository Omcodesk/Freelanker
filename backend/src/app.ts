import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { env } from './config/env.js';
import healthRouter from './routes/health.route.js';
import authRouter from './routes/auth.route.js';
import projectRouter from './routes/project.route.js';
import invitationRouter from './routes/invitation.route.js';
import contractflowRouter from './routes/contractflow.route.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';

const app = express();

// ─── Security Middleware ───────────────────────────────────────────────────────
app.use(helmet());

// ─── CORS ─────────────────────────────────────────────────────────────────────
const allowedOriginsSet = new Set(env.ALLOWED_ORIGINS);

app.use(
  cors({
    origin: (requestOrigin, callback) => {
      // Allow server-to-server or non-browser tools (curl, Postman, server health checks)
      if (!requestOrigin) {
        callback(null, true);
        return;
      }

      const normalized = requestOrigin.trim().replace(/\/+$/, '');
      if (allowedOriginsSet.has(normalized)) {
        callback(null, true);
      } else {
        callback(new Error(`Origin '${requestOrigin}' not allowed by CORS.`));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);

// ─── Body Parsing ─────────────────────────────────────────────────────────────
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// ─── Routes ───────────────────────────────────────────────────────────────────
app.use('/api/health', healthRouter);
app.use('/api/auth', authRouter);
app.use('/api/projects', projectRouter);
app.use('/api/invitations', invitationRouter);
app.use('/api/contractflow', contractflowRouter);

// Person 3: WorkBridge router will be mounted here on merge
// app.use('/api/workbridge', workbridgeRouter);

// ─── 404 & Error Handlers ─────────────────────────────────────────────────────
app.use(notFoundHandler);
app.use(errorHandler);

export default app;

