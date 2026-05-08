import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { sessionApi, chatApi } from '../services/api';
import { useAuthStore } from '../store';
import type { Session, Message } from '../types';

const Chat: React.FC = () => {
  const { t } = useTranslation();
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const { user, hasPermission } = useAuthStore();
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadSession = async (id: string) => {
    setLoading(true);
    try {
      const sessionData = await sessionApi.getSession(id);
      setSession(sessionData);
      const msgs = await sessionApi.getSessionMessages(id);
      setMessages(msgs);
    } catch (error) {
      console.error('Failed to load session:', error);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!input.trim() || !session) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      sessionId: session.id,
      role: 'agent',
      content: input,
      timestamp: new Date().toISOString()
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      const response = await chatApi.sendMessage(session.userId, input);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        sessionId: session.id,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleBack = () => {
    navigate('/sessions');
  };

  const handleEndChat = async () => {
    if (!session) return;
    try {
      await sessionApi.releaseSession(session.id);
      navigate('/sessions');
    } catch (error) {
      console.error('Failed to end chat:', error);
    }
  };

  const getMessageClass = (role: string) => {
    switch (role) {
      case 'user':
        return 'chat-message user';
      case 'assistant':
        return 'chat-message assistant';
      case 'agent':
        return 'chat-message agent';
      case 'system':
        return 'chat-message system';
      default:
        return 'chat-message';
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4 flex justify-between items-center">
        <div>
          <button onClick={handleBack} className="text-gray-500 hover:text-gray-700 mb-2">
            ← {t('sessions.viewHistory')}
          </button>
          <h1 className="text-2xl font-bold text-gray-800">{t('chat.title')}</h1>
          {session && (
            <p className="text-sm text-gray-500">
              {t('sessions.userId')}: {session.userId} | {t('sessions.sessionId')}: {session.id.slice(0, 8)}...
            </p>
          )}
        </div>
        {session && (
          <button onClick={handleEndChat} className="btn-secondary text-red-600">
            {t('chat.endChat')}
          </button>
        )}
      </div>

      <div className="flex-1 card flex flex-col overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-gray-500">{t('common.loading')}</div>
          </div>
        ) : !sessionId ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-4">💬</div>
              <p>{t('sessions.title')}</p>
              <a href="/sessions" className="text-primary-600 hover:underline mt-2 inline-block">
                {t('sessions.sessionList')}
              </a>
            </div>
          </div>
        ) : (
          <>
            <div className="chat-messages flex-1 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  {t('common.noData')}
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={getMessageClass(msg.role)}>
                    <div className="text-xs opacity-75 mb-1">
                      {msg.role === 'user' ? t('chat.customerMessage') :
                       msg.role === 'assistant' ? 'AI' :
                       msg.role === 'agent' ? t('chat.agentMessage') :
                       t('chat.systemMessage')}
                    </div>
                    <div>{msg.content}</div>
                    <div className="text-xs opacity-50 mt-1">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {hasPermission('reply_sessions') && session?.status === 'transferred' && (
              <div className="chat-input">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={t('chat.placeholder')}
                  className="flex-1"
                  disabled={sending}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sending}
                  className="btn-primary"
                >
                  {sending ? t('common.loading') : t('chat.send')}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Chat;
