import React, { useState } from 'react';
import { AlertTriangle, Send, Loader2 } from 'lucide-react';

interface OutageFormProps {
  onSubmit: (data: {
    description: string;
    affected_services: string[];
    severity: string;
    additional_context: string;
  }) => void;
  isLoading: boolean;
}

const SEVERITY_OPTIONS = ['P1', 'P2', 'P3'];
const SERVICE_OPTIONS = [
  'PilotFish-Core',
  'PilotFish-API',
  'PilotFish-Scheduler',
  'PilotFish-Agent',
  'Identity-Service',
  'Config-Service',
  'Storage-Service',
  'Monitoring-Service',
];

export const OutageForm: React.FC<OutageFormProps> = ({ onSubmit, isLoading }) => {
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('P1');
  const [selectedServices, setSelectedServices] = useState<string[]>([]);
  const [additionalContext, setAdditionalContext] = useState('');

  const toggleService = (service: string) => {
    setSelectedServices(prev =>
      prev.includes(service) ? prev.filter(s => s !== service) : [...prev, service]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    onSubmit({
      description,
      affected_services: selectedServices,
      severity,
      additional_context: additionalContext,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-5">
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle className="text-orange-400" size={20} />
        <h2 className="text-lg font-bold text-white">Report Outage</h2>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Outage Description <span className="text-red-400">*</span>
        </label>
        <textarea
          className="input-field min-h-[120px] resize-y"
          placeholder="Describe what is failing, symptoms observed, error messages..."
          value={description}
          onChange={e => setDescription(e.target.value)}
          required
          disabled={isLoading}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Severity</label>
        <div className="flex gap-2">
          {SEVERITY_OPTIONS.map(sev => (
            <button
              key={sev}
              type="button"
              onClick={() => setSeverity(sev)}
              className={`px-4 py-1.5 rounded-lg text-sm font-semibold border transition-colors ${
                severity === sev
                  ? sev === 'P1'
                    ? 'bg-red-700 border-red-500 text-white'
                    : sev === 'P2'
                    ? 'bg-orange-700 border-orange-500 text-white'
                    : 'bg-yellow-700 border-yellow-500 text-white'
                  : 'bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-400'
              }`}
              disabled={isLoading}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Affected Services
        </label>
        <div className="flex flex-wrap gap-2">
          {SERVICE_OPTIONS.map(svc => (
            <button
              key={svc}
              type="button"
              onClick={() => toggleService(svc)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                selectedServices.includes(svc)
                  ? 'bg-blue-700 border-blue-500 text-white'
                  : 'bg-gray-800 border-gray-600 text-gray-400 hover:border-blue-500'
              }`}
              disabled={isLoading}
            >
              {svc}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Additional Context
        </label>
        <textarea
          className="input-field min-h-[80px] resize-y"
          placeholder="Recent deployments, config changes, error logs..."
          value={additionalContext}
          onChange={e => setAdditionalContext(e.target.value)}
          disabled={isLoading}
        />
      </div>

      <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={isLoading || !description.trim()}>
        {isLoading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Analyzing Outage...
          </>
        ) : (
          <>
            <Send size={16} />
            Generate Recovery Plan
          </>
        )}
      </button>
    </form>
  );
};
