import { Request, Response, NextFunction } from 'express';
import { supabaseAuth } from '../lib/supabase.js';
import { errorResponse } from '../types/index.js';

// Extend Express Request interface to carry verified user context
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        email: string;
        isEmailVerified: boolean;
        emailConfirmedAt?: string | null;
        createdAt: string;
        userMetadata?: Record<string, unknown>;
      };
    }
  }
}

/**
 * Strict authentication middleware.
 * Verifies the Supabase JWT access token on the server side via Supabase Auth.
 * Rejects requests with 401 if missing, invalid, or expired.
 * Never trusts client-supplied user IDs.
 */
export async function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    res.status(401).json(errorResponse('Authentication required: Missing or malformed Authorization header.'));
    return;
  }

  const token = authHeader.split(' ')[1]?.trim();

  if (!token) {
    res.status(401).json(errorResponse('Authentication required: Token missing.'));
    return;
  }

  try {
    const {
      data: { user },
      error,
    } = await supabaseAuth.auth.getUser(token);

    if (error || !user) {
      res.status(401).json(errorResponse(error?.message || 'Unauthorized: Invalid or expired access token.'));
      return;
    }

    // Attach verified user identity from Supabase Auth server.
    // Never trust caller-writable user_metadata for email verification.
    const isEmailVerified = Boolean(user.email_confirmed_at);
    req.user = {
      id: user.id,
      email: user.email ?? '',
      isEmailVerified,
      emailConfirmedAt: user.email_confirmed_at ?? null,
      createdAt: user.created_at,
      userMetadata: user.user_metadata,
    };

    next();
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Token verification failed.';
    res.status(401).json(errorResponse(message));
  }
}

/**
 * Optional authentication middleware.
 * Populates req.user if a valid token is provided, but continues if not.
 */
export async function optionalAuth(
  req: Request,
  _res: Response,
  next: NextFunction
): Promise<void> {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return next();
  }

  const token = authHeader.split(' ')[1]?.trim();
  if (!token) {
    return next();
  }

  try {
    const {
      data: { user },
      error,
    } = await supabaseAuth.auth.getUser(token);

    if (!error && user) {
      const isEmailVerified = Boolean(user.email_confirmed_at);
      req.user = {
        id: user.id,
        email: user.email ?? '',
        isEmailVerified,
        emailConfirmedAt: user.email_confirmed_at ?? null,
        createdAt: user.created_at,
        userMetadata: user.user_metadata,
      };
    }
  } catch {
    // Continue unauthenticated on error
  }

  next();
}
