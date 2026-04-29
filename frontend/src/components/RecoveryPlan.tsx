import React from 'react';
import { AlertTriangle, Clock, CheckCircle2, BookOpen, ChevronRight } from 'lucide-react';
import type { RecoveryPlan, RecoveryStep } from '../types';

interface RecoveryPlanProps {
  plan: RecoveryPlan;
}

const RiskBadge: React.FC<{ risk: RecoveryStep['risk_level'] }> = ({ risk }) => {
  const cls =
    risk === 'LOW' ? 'badge-low' : risk === 'MEDIUM' ? 'badge-medium' : 'badge-high';
  return <span className={cls}>{risk}</span>;
};

export const RecoveryPlanDisplay: React.FC<RecoveryPlanProps> = ({ plan }) => {
  return (
    <div className="space-y-5">
      {/* Summary Card */}
      <div className="card border-blue-700">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-lg font-bold text-white mb-2">Recovery Plan</h2>
            <p className="text-gray-300 text-sm leading-relaxed">{plan.summary}</p>
          </div>
          <div className="text-right shrink-0">
            <div className="flex items-center gap-1 text-blue-400 font-semibold">
              <Clock size={16} />
              <span className="text-sm">{plan.estimated_total_rto}</span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">Est. RTO</div>
          </div>
        </div>
        {plan.affected_services.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {plan.affected_services.map(svc => (
              <span key={svc} className="bg-gray-800 text-gray-300 text-xs px-2 py-0.5 rounded border border-gray-600">
                {svc}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Warnings */}
      {plan.warnings.length > 0 && (
        <div className="bg-yellow-950 border border-yellow-700 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-yellow-400" />
            <span className="text-yellow-300 font-semibold text-sm">Warnings</span>
          </div>
          <ul className="space-y-1">
            {plan.warnings.map((w, i) => (
              <li key={i} className="text-yellow-200 text-sm flex items-start gap-2">
                <ChevronRight size={14} className="mt-0.5 shrink-0 text-yellow-500" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Steps */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Recovery Steps ({plan.recovery_steps.length})
        </h3>
        {plan.recovery_steps.map(step => (
          <div key={step.step_number} className="card hover:border-gray-500 transition-colors">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-800 border border-blue-600 flex items-center justify-center text-blue-200 text-xs font-bold">
                {step.step_number}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <h4 className="font-semibold text-white text-sm">{step.action}</h4>
                  <RiskBadge risk={step.risk_level} />
                </div>
                <p className="text-gray-400 text-xs mb-2">{step.rationale}</p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1.5 text-gray-400">
                    <Clock size={12} className="text-gray-500" />
                    <span>{step.estimated_duration}</span>
                  </div>
                  {step.dependencies.length > 0 && (
                    <div className="flex items-start gap-1.5 text-gray-400">
                      <ChevronRight size={12} className="text-gray-500 mt-0.5 shrink-0" />
                      <span>Requires: {step.dependencies.join(', ')}</span>
                    </div>
                  )}
                </div>

                <div className="mt-2 flex items-start gap-1.5 text-xs text-green-400">
                  <CheckCircle2 size={12} className="mt-0.5 shrink-0" />
                  <span>{step.verification}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Knowledge Sources */}
      {plan.knowledge_sources.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <BookOpen size={12} />
          <span>Sources: {plan.knowledge_sources.join(' · ')}</span>
        </div>
      )}
    </div>
  );
};
