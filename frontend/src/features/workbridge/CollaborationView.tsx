import { useEffect, useState } from 'react';
import { api, ApiError } from '../../services/api.ts';
import { useAuth } from '../auth/AuthContext.tsx';

export interface DiscussionMessage {
  id: string;
  projectId: string;
  senderId: string;
  content: string;
  fileUrls: string[];
  isAiSummary: boolean;
  createdAt: string;
  senderProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

interface CollaborationViewProps {
  projectId: string;
}

export function CollaborationView({ projectId }: CollaborationViewProps) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<DiscussionMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inputContent, setInputContent] = useState('');
  const [sending, setSending] = useState(false);

  const loadMessages = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<DiscussionMessage[]>(`/workbridge/projects/${projectId}/messages`);
      setMessages(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load messages.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, [projectId]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputContent.trim()) return;

    setSending(true);
    try {
      const created = await api.post<DiscussionMessage>(
        `/workbridge/projects/${projectId}/messages`,
        { content: inputContent.trim() }
      );
      setMessages((prev) => [...prev, created]);
      setInputContent('');
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed to post message.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900">Project Collaboration & Discussion</h3>
        <p className="text-xs text-slate-500">
          Direct communication, updates, and feedback between project members.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Messages Feed */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 min-h-[300px] max-h-[500px] overflow-y-auto space-y-3">
        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">Loading messages...</div>
        ) : messages.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No messages yet. Start the conversation with your team below.
          </div>
        ) : (
          messages.map((msg) => {
            const isMe = msg.senderId === user?.id;
            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isMe ? 'justify-end' : 'justify-start'}`}
              >
                {!isMe && (
                  <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center shrink-0">
                    {(msg.senderProfile?.displayName || 'U')[0].toUpperCase()}
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-2xl p-3.5 space-y-1 shadow-sm ${
                    isMe
                      ? 'bg-brand-600 text-white rounded-tr-none'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
                  }`}
                >
                  <div
                    className={`flex items-center gap-2 text-[10px] ${
                      isMe ? 'text-brand-100 justify-end' : 'text-slate-400'
                    }`}
                  >
                    <span className="font-semibold">
                      {isMe ? 'You' : msg.senderProfile?.displayName || 'Member'}
                    </span>
                    <span>•</span>
                    <span>{new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <p className="text-xs whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Post Box */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={inputContent}
          onChange={(e) => setInputContent(e.target.value)}
          placeholder="Type an update or comment..."
          className="flex-1 px-4 py-2.5 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          type="submit"
          disabled={sending || !inputContent.trim()}
          className="px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition-colors shadow-sm"
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
