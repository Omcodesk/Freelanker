import { Request, Response, NextFunction } from 'express';
import { errorResponse } from '../types/index.js';
import { env } from '../config/env.js';

export interface AppError extends Error {
  statusCode?: number;
}

export function errorHandler(
  err: AppError,
  _req: Request,
  res: Response,
  _next: NextFunction
): void {
  const statusCode = err.statusCode ?? 500;
  const message =
    env.isDevelopment
      ? err.message
      : statusCode === 500
        ? 'Internal server error'
        : err.message;

  if (env.isDevelopment) {
    console.error('[Error]', err.stack);
  }

  res.status(statusCode).json(errorResponse(message));
}

export function notFoundHandler(_req: Request, res: Response): void {
  res.status(404).json(errorResponse('Route not found'));
}

