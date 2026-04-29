import { useState } from 'react';
import axios from 'axios';
import { Shield, Github, AlertCircle } from 'lucide-react';
import { OutageForm } from './components/OutageForm';
import { RecoveryPlanDisplay } from './components/RecoveryPlan';
import { ChatInterface } from './components/ChatInterface';
import { DependencyPanel } from './components/DependencyPanel';
import type { RecoveryPlan, ChatMessage } from './types';

function App() {
  const [plan, setPlan] = useState<RecoveryPlan | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (formData: {
    description: string;
    affected_services: string[];
    severity: string;
    additional_context: string;
  }) => {
    setIsAnalyzing(true);
    setError(null);
    setPlan(null);
    setChatMessages([]);

    try {
      const { data } = await axios.post<RecoveryPlan>('/api/v1/advisor/analyze', formData);
      setPlan(data);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || err.message || 'Failed to analyze outage');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!plan) return;

    const userMsg: ChatMessage = { role: 'user', content: message, timestamp: new Date() };
    setChatMessages(prev => [...prev, userMsg]);
    setIsChatLoading(true);

    try {
      const { data } = await axios.post('/api/v1/advisor/chat', {
        session_id: plan.session_id,
        message,
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, assistantMsg]);
    } catch (_err) {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: 'Failed to get response. Please try again.',
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errMsg]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <Shield className="text-blue-400" size={24} />
          <div>
            <h1 className="text-lg font-bold text-white leading-tight">PFR Recovery Advisor</h1>
            <p className="text-xs text-gray-400">AI-powered PilotFish control plane recovery</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs bg-green-900 text-green-300 border border-green-700 px-2 py-0.5 rounded-full">
              Live
            </span>
            <a
              href="https://github.com/Banreet/PFR-Recovery-Advisor"
              target="_blank"
              rel="noreferrer"
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="GitHub repository"
            >
              <Github size={18} />
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-5 bg-red-950 border border-red-700 rounded-xl p-4 flex items-start gap-2">
            <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-1 space-y-5">
            <OutageForm onSubmit={handleAnalyze} isLoading={isAnalyzing} />
            <DependencyPanel
              affectedServices={plan?.affected_services ?? []}
            />
          </div>

          {/* Right Column */}
          <div className="lg:col-span-2 space-y-5">
            {!plan && !isAnalyzing && (
              <div className="card flex flex-col items-center justify-center py-20 text-center">
                <Shield size={48} className="text-gray-700 mb-4" />
                <h2 className="text-xl font-semibold text-gray-400 mb-2">
                  Ready to Assist
                </h2>
                <p className="text-gray-600 text-sm max-w-sm">
                  Describe your outage in the form on the left to generate an
                  AI-powered, dependency-aware recovery plan.
                </p>
              </div>
            )}

            {isAnalyzing && (
              <div className="card flex flex-col items-center justify-center py-20 text-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-gray-300 font-medium">Analyzing outage...</p>
                <p className="text-gray-500 text-sm mt-1">Generating recovery plan with AI</p>
              </div>
            )}

            {plan && !isAnalyzing && (
              <>
                <RecoveryPlanDisplay plan={plan} />
                <ChatInterface
                  sessionId={plan.session_id}
                  messages={chatMessages}
                  onSendMessage={handleSendMessage}
                  isLoading={isChatLoading}
                />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
