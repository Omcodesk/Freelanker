import { Request, Response } from 'express';
import { supabaseAdmin } from '../lib/supabase.js';
import { successResponse, errorResponse } from '../types/index.js';

/**
 * GET /api/auth/me
 * Returns the currently authenticated user and their profile.
 * Protected by requireAuth middleware.
 */
export async function getMe(req: Request, res: Response): Promise<void> {
  const user = req.user;

  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  try {
    // Fetch user profile from public.profiles
    const { data: profile, error } = await supabaseAdmin
      .from('profiles')
      .select('*')
      .eq('id', user.id)
      .maybeSingle();

    if (error) {
      console.error('[Auth Controller] Error fetching profile:', error.message);
    }

    res.status(200).json(
      successResponse({
        user: {
          id: user.id,
          email: user.email,
          createdAt: user.createdAt,
          userMetadata: user.userMetadata,
        },
        profile: profile
          ? {
              id: profile.id,
              displayName: profile.display_name,
              headline: profile.headline,
              bio: profile.bio,
              avatarUrl: profile.avatar_url,
              skills: profile.skills,
              portfolioLinks: profile.portfolio_links,
              isAvailable: profile.is_available,
              isAdmin: profile.is_admin,
              createdAt: profile.created_at,
              updatedAt: profile.updated_at,
            }
          : null,
      })
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to retrieve profile.';
    res.status(500).json(errorResponse(message));
  }
}
