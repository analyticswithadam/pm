"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, X, Sparkles, MessageSquare } from "lucide-react";
import { BoardData } from "@/lib/kanban";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatSidebarProps {
  board: BoardData;
  onRefreshBoard: () => Promise<void>;
}

export const ChatSidebar = ({ board, onRefreshBoard }: ChatSidebarProps) => {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          history: messages,
          board: board,
        }),
      });

      const data = await response.json();
      
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      
      if (data.commands && data.commands.length > 0) {
        // If the AI modified the board, refresh the frontend state
        await onRefreshBoard();
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error connecting to the AI." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full w-full min-w-[320px] flex-col rounded-[32px] border border-[var(--stroke)] bg-white shadow-[var(--shadow)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--stroke)] bg-[var(--navy-dark)] p-6 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--primary-blue)]">
            <Bot size={24} />
          </div>
          <div>
            <h2 className="font-display text-lg font-bold">AI Assistant</h2>
            <div className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                Online
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-[var(--surface)]">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center opacity-60">
            <Sparkles size={40} className="text-[var(--primary-blue)] mb-4" />
            <p className="text-xs text-[var(--gray-text)] font-medium leading-relaxed">
              Ask me to "Add a card to Backlog"<br />
              or "Move card-1 to Done".
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`flex gap-3 max-w-[90%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white ${
                msg.role === "user" ? "bg-[var(--secondary-purple)]" : "bg-[var(--primary-blue)]"
              }`}>
                {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className={`rounded-2xl px-3 py-2 text-xs shadow-sm ${
                msg.role === "user" 
                  ? "bg-white text-[var(--navy-dark)] rounded-tr-none border border-[var(--stroke)]" 
                  : "bg-[var(--navy-dark)] text-white rounded-tl-none"
              }`}>
                {msg.content}
              </div>
            </div>
          </motion.div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--primary-blue)] text-white">
                <Bot size={14} />
              </div>
              <div className="flex items-center gap-1 rounded-2xl bg-[var(--navy-dark)] px-3 py-2">
                <div className="h-1 w-1 animate-bounce rounded-full bg-white/40" />
                <div className="h-1 w-1 animate-bounce rounded-full bg-white/40 [animation-delay:0.2s]" />
                <div className="h-1 w-1 animate-bounce rounded-full bg-white/40 [animation-delay:0.4s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-[var(--stroke)] p-4 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a command..."
            className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] py-3 pl-4 pr-12 text-xs focus:border-[var(--primary-blue)] focus:outline-none transition-all"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-1.5 top-1.5 flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--secondary-purple)] text-white transition hover:scale-105 active:scale-95 disabled:opacity-50"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
};
