import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User } from 'lucide-react';
import type { ChatMessage } from '../types';

interface ChatInterfaceProps {
  sessionId: string;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  messages,
  onSendMessage,
  isLoading,
}) => {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="card flex flex-col h-[420px]">
      <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
        <Bot size={16} className="text-blue-400" />
        Recovery Assistant
        <span className="ml-auto text-xs text-gray-500 font-normal truncate max-w-[140px]" title={sessionId}>
          Session: {sessionId.slice(0, 8)}...
        </span>
      </h3>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mb-3">
        {messages.length === 0 && (
          <p className="text-gray-500 text-sm text-center mt-8">
            Ask follow-up questions about the recovery plan
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-6 h-6 rounded-full bg-blue-800 flex items-center justify-center mt-0.5">
                <Bot size={12} className="text-blue-300" />
              </div>
            )}
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-700 text-white'
                  : 'bg-gray-800 text-gray-200'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="shrink-0 w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center mt-0.5">
                <User size={12} className="text-gray-300" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-2 justify-start">
            <div className="shrink-0 w-6 h-6 rounded-full bg-blue-800 flex items-center justify-center">
              <Bot size={12} className="text-blue-300" />
            </div>
            <div className="bg-gray-800 rounded-xl px-3 py-2">
              <Loader2 size={14} className="animate-spin text-blue-400" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 border-t border-gray-700 pt-3">
        <textarea
          className="input-field flex-1 resize-none min-h-[38px] max-h-[80px] text-sm py-2"
          placeholder="Ask about recovery steps, risks, or next actions... (Enter to send)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="btn-primary px-3 py-2 self-end"
          aria-label="Send message"
        >
          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
};
