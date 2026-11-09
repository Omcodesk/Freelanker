import { Request, Response } from 'express';
import { successResponse, type HealthData } from '../types/index.js';
import { env } from '../config/env.js';

export function getHealth(_req: Request, res: Response): void {
  const data: HealthData = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    environment: env.NODE_ENV,
  };

  res.status(200).json(successResponse(data));
}
