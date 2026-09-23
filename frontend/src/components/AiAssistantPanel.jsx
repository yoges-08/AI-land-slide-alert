import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  X,
  Send,
  RotateCcw,
  MapPin,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Database,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Info,
  Layers,
  ArrowRight
} from 'lucide-react';
import { sendAssistantChat } from '../services/api';

export default function AiAssistantPanel({
  isOpen,
  onClose,
  selectedLocation,
  onSelectLocation
}) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: `### 👋 Welcome to LANDSAFE-NER AI Assistant\n\nI provide **grounded meteorological & multi-hazard intelligence** across all 788 LGD districts in India.\n\n**What you can ask me:**\n- 🌦️ *"Rain in Wayanad tomorrow?"* or 5-day weather forecasts.\n- 📊 *"Top 5 high landslide risk districts in Kerala"* (cross-district ranking).\n- 🌐 *"Recent earthquake activity near Northeast India"* (USGS/NCS real-time).\n- 🏔️ *"Landslide and soil saturation assessment for Gangtok"*.\n- 🛡️ *"Safety guidelines for heavy rainfall and slope failure"*.\n\n> [!NOTE]\n> All data is strictly derived from live Open-Meteo, Sentinel-2/1, NASA FIRMS, and GSI models with zero fabrication.`,
      sources: ['LANDSAFE-NER Core', 'LGD 788 Database'],
      tools_used: ['system_init'],
      timestamp_ist: new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST',
      advisory: 'Advisory only. IMD, NDMA and NCS are the sole official warning authorities in India.',
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
      scrollToBottom();
    }
  }, [isOpen, messages]);

  const handleSend = async (queryToSend = null) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || isLoading) return;

    const userMsgId = `user-${Date.now()}`;
    const newMsgList = [
      ...messages,
      {
        id: userMsgId,
        role: 'user',
        content: text,
        timestamp_ist: new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST',
      }
    ];

    setMessages(newMsgList);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await sendAssistantChat(
        text,
        selectedLocation,
        newMsgList.filter((m) => m.id !== 'welcome-msg')
      );

      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: response.reply,
          sources: response.sources || ['Open-Meteo Live'],
          tools_used: response.tools_used || [],
          timestamp_ist: response.timestamp_ist,
          context_location: response.context_location,
          advisory: response.advisory,
        }
      ]);
    } catch (err) {
      console.error('Assistant error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-err-${Date.now()}`,
          role: 'assistant',
          content: '⚠️ Failed to receive response from assistant. Please try again.',
          sources: ['Error Handler'],
          timestamp_ist: new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST',
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: 'assistant',
        content: `Chat session cleared. You can ask about weather, hazard susceptibility, earthquake activity, or safety protocols across any of India's 788 LGD districts.`,
        sources: ['LANDSAFE-NER Core'],
        timestamp_ist: new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST',
      }
    ]);
  };

  const suggestedPrompts = [
    `Rain in ${selectedLocation?.name || 'Wayanad'} tomorrow?`,
    `Top 5 high landslide risk districts in ${selectedLocation?.state || 'Kerala'}`,
    `Recent earthquake activity near Northeast India`,
    `Landslide safety guidelines and citizen actions`,
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Dark backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity animate-fade-in"
      />

      {/* Slide-over Drawer */}
      <aside className="relative w-full sm:w-[440px] md:w-[480px] bg-white h-full shadow-2xl flex flex-col z-10 border-l border-slate-200 transform transition-transform duration-300 ease-out animate-slide-in-right">
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-200/90 bg-slate-900 text-white flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4 fill-slate-950 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold tracking-tight">AI Weather & Hazard Assistant</h2>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider">
                  Beta
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Grounded Telemetry • IMD/NDMA Aligned</p>
            </div>
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={handleClearHistory}
              title="Clear Conversation"
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              title="Close Assistant (Esc)"
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Dashboard Context Chip */}
        {selectedLocation && (
          <div className="px-4 py-2 bg-emerald-50/70 border-b border-emerald-100/80 flex items-center justify-between text-xs text-emerald-900 flex-shrink-0">
            <div className="flex items-center space-x-1.5 overflow-hidden">
              <MapPin className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
              <span className="font-semibold truncate">
                Context: {selectedLocation.name}, {selectedLocation.state}
              </span>
            </div>
            <span className="text-[10px] text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
              Active Sync
            </span>
          </div>
        )}

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/60 text-xs">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              {/* Message Bubble */}
              <div
                className={`max-w-[92%] rounded-2xl p-3.5 shadow-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-slate-900 text-white rounded-br-xs'
                    : 'bg-white text-slate-800 border border-slate-200/90 rounded-bl-xs'
                }`}
              >
                {/* Content Renderer */}
                <FormattedMarkdown content={msg.content} />

                {/* Footer Metadata for Assistant */}
                {msg.role === 'assistant' && (
                  <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-1.5 text-[10px] text-slate-400">
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{msg.timestamp_ist || 'Live IST'}</span>
                    </div>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="flex items-center space-x-1">
                        <Database className="w-3 h-3 text-emerald-600" />
                        <span className="font-medium text-slate-600 truncate max-w-[180px]">
                          {msg.sources.join(' • ')}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex items-start space-x-2">
              <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-xs px-4 py-3 shadow-xs flex items-center space-x-2 text-slate-500">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[11px] font-medium text-slate-600">Querying live telemetry & GSI models...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompts Pill Carousel */}
        <div className="px-3.5 py-2 bg-white border-t border-slate-100 flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-shrink-0">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex-shrink-0">
            Ask:
          </span>
          {suggestedPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              disabled={isLoading}
              className="text-[11px] whitespace-nowrap px-2.5 py-1 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300 border border-slate-200/80 rounded-lg text-slate-700 font-medium transition-all flex-shrink-0"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3.5 bg-white border-t border-slate-200/90 flex-shrink-0">
          <div className="relative flex items-center">
            <textarea
              ref={inputRef}
              rows={2}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask about rainfall, hazard risk, or earthquakes in any district...`}
              disabled={isLoading}
              className="w-full pl-3 pr-10 py-2 bg-slate-50 hover:bg-slate-100/60 focus:bg-white text-xs text-slate-800 placeholder-slate-400 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 resize-none transition-all leading-snug"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputQuery.trim() || isLoading}
              className="absolute right-2 bottom-2 p-2 bg-slate-900 hover:bg-emerald-600 disabled:opacity-40 text-white rounded-lg transition-all shadow-xs"
              title="Send Message (Enter)"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400 px-1">
            <span>Press <kbd className="font-mono bg-slate-100 px-1 rounded border border-slate-200">Enter</kbd> to send</span>
            <span className="text-amber-700/80 font-medium">IMD/NDMA/NCS are sole official warning authorities</span>
          </div>
        </div>
      </aside>
    </div>
  );
}


/**
 * Clean markdown formatter supporting headings, bolding, bullet points,
 * tables, blockquotes, and callouts without requiring heavy third-party parsers.
 */
function FormattedMarkdown({ content = '' }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let tableRows = [];
  let inTable = false;

  const flushTable = (key) => {
    if (tableRows.length > 0) {
      const header = tableRows[0];
      const dataRows = tableRows.slice(1).filter((r) => !r.every((c) => c.match(/^[:\-\s]+$/)));

      elements.push(
        <div key={`table-${key}`} className="my-2.5 overflow-x-auto rounded-lg border border-slate-200 text-[11px]">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-100/90 text-slate-800 font-semibold border-b border-slate-200">
                {header.map((col, idx) => (
                  <th key={idx} className="px-2.5 py-1.5 text-left whitespace-nowrap">
                    {formatInline(col)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataRows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className={`border-b border-slate-100 last:border-b-0 ${
                    rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'
                  } hover:bg-emerald-50/30 transition-colors`}
                >
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-2.5 py-1.5 text-slate-700 whitespace-nowrap">
                      {formatInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Table rows starting and ending with |
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      inTable = true;
      const cells = line
        .trim()
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim());
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      flushTable(i);
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={i} className="text-xs font-bold text-slate-900 mt-2 mb-1 flex items-center gap-1.5">
          {formatInline(line.replace('### ', ''))}
        </h4>
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h3 key={i} className="text-sm font-bold text-slate-900 mt-2.5 mb-1.5">
          {formatInline(line.replace('## ', ''))}
        </h3>
      );
    }
    // Blockquote / Alert
    else if (line.startsWith('> [!NOTE]') || line.startsWith('> [!IMPORTANT]') || line.startsWith('> [!WARNING]')) {
      const isNote = line.includes('NOTE');
      const isWarning = line.includes('WARNING');
      elements.push(
        <div
          key={i}
          className={`my-2 p-2.5 rounded-lg border text-[11px] ${
            isWarning
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
          }`}
        >
          <div className="font-bold flex items-center space-x-1.5 mb-0.5">
            <Info className="w-3.5 h-3.5 text-emerald-700 flex-shrink-0" />
            <span>Advisory Notice</span>
          </div>
          <div className="leading-relaxed">
            {formatInline(lines[i + 1]?.replace(/^>\s*/, '') || '')}
          </div>
        </div>
      );
      i++; // Skip next line if consumed
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote
          key={i}
          className="my-2 pl-3 border-l-2 border-emerald-500 text-slate-600 text-[11px] italic bg-slate-50/50 py-1"
        >
          {formatInline(line.replace(/^>\s*/, ''))}
        </blockquote>
      );
    }
    // Bullet point
    else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      elements.push(
        <li key={i} className="ml-3.5 list-disc text-slate-700 my-0.5 leading-relaxed">
          {formatInline(line.trim().replace(/^[-*]\s*/, ''))}
        </li>
      );
    }
    // Numbered list
    else if (line.trim().match(/^\d+\.\s/)) {
      elements.push(
        <div key={i} className="ml-1 my-0.5 flex items-start space-x-1.5 text-slate-700 leading-relaxed">
          <span className="font-semibold text-slate-900 text-[11px]">
            {line.trim().match(/^\d+\./)[0]}
          </span>
          <span>{formatInline(line.trim().replace(/^\d+\.\s*/, ''))}</span>
        </div>
      );
    }
    // Blank line
    else if (!line.trim()) {
      elements.push(<div key={i} className="h-1.5" />);
    }
    // Regular paragraph
    else {
      elements.push(
        <p key={i} className="my-1 leading-relaxed text-slate-700">
          {formatInline(line)}
        </p>
      );
    }
  }

  if (inTable) flushTable('end');

  return <div className="space-y-0.5">{elements}</div>;
}


/**
 * Inline formatting for bold, italic, code pills, and citations.
 */
function formatInline(text = '') {
  if (!text) return '';

  // Split by bold (**text**), code (`text`), and citations ([Source])
  const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[.*?\])/g);

  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={idx} className="font-bold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={idx} className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[10px] font-mono border border-slate-200">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('[') && part.endsWith(']')) {
      return (
        <span key={idx} className="text-emerald-700 font-semibold text-[10px] bg-emerald-50 px-1 py-0.2 rounded border border-emerald-200">
          {part}
        </span>
      );
    }
    return part;
  });
}
