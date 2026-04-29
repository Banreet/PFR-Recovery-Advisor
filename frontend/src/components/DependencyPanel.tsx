import React from 'react';
import { GitBranch, Circle } from 'lucide-react';

interface Service {
  depends_on: string[];
  description: string;
  recovery_priority: number;
  typical_startup_time?: string;
}

interface DependencyPanelProps {
  affectedServices: string[];
  allServices?: Record<string, Service>;
}

const BUILTIN_SERVICES: Record<string, Service> = {
  'PilotFish-Core': { depends_on: ['Identity-Service', 'Config-Service', 'Storage-Service'], description: 'Core control plane', recovery_priority: 1 },
  'PilotFish-API': { depends_on: ['PilotFish-Core', 'Identity-Service'], description: 'REST API gateway', recovery_priority: 2 },
  'PilotFish-Scheduler': { depends_on: ['PilotFish-Core', 'Storage-Service'], description: 'Job scheduling', recovery_priority: 3 },
  'PilotFish-Agent': { depends_on: ['PilotFish-API'], description: 'Compute node agent', recovery_priority: 4 },
  'Identity-Service': { depends_on: [], description: 'Auth & authorization', recovery_priority: 0 },
  'Config-Service': { depends_on: ['Identity-Service'], description: 'Configuration management', recovery_priority: 0 },
  'Storage-Service': { depends_on: ['Identity-Service'], description: 'Distributed storage', recovery_priority: 0 },
  'Monitoring-Service': { depends_on: ['PilotFish-Core', 'Storage-Service'], description: 'Metrics & alerting', recovery_priority: 5 },
};

const priorityColors: Record<number, string> = {
  0: 'text-green-400',
  1: 'text-blue-400',
  2: 'text-blue-300',
  3: 'text-yellow-400',
  4: 'text-orange-400',
  5: 'text-gray-400',
};

export const DependencyPanel: React.FC<DependencyPanelProps> = ({
  affectedServices,
  allServices,
}) => {
  const services = allServices || BUILTIN_SERVICES;
  const displayServices = affectedServices.length > 0 ? affectedServices : Object.keys(services);

  const sorted = [...displayServices].sort((a, b) => {
    const pa = services[a]?.recovery_priority ?? 99;
    const pb = services[b]?.recovery_priority ?? 99;
    return pa - pb;
  });

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch size={16} className="text-purple-400" />
        <h3 className="text-sm font-bold text-white">Service Dependencies</h3>
        {affectedServices.length > 0 && (
          <span className="ml-auto text-xs bg-purple-900 text-purple-300 border border-purple-700 px-2 py-0.5 rounded-full">
            {affectedServices.length} affected
          </span>
        )}
      </div>

      <div className="space-y-2.5">
        {sorted.map(svcName => {
          const svc = services[svcName];
          const isAffected = affectedServices.includes(svcName);
          const priority = svc?.recovery_priority ?? 99;
          const colorClass = priorityColors[priority] ?? 'text-gray-400';

          return (
            <div
              key={svcName}
              className={`rounded-lg p-3 border transition-colors ${
                isAffected
                  ? 'bg-red-950 border-red-800'
                  : 'bg-gray-800 border-gray-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <Circle
                  size={8}
                  className={`shrink-0 ${isAffected ? 'text-red-400 fill-red-400' : colorClass + ' fill-current opacity-60'}`}
                />
                <span className={`text-sm font-medium ${isAffected ? 'text-red-200' : 'text-gray-200'}`}>
                  {svcName}
                </span>
                {priority <= 1 && (
                  <span className="ml-auto text-xs text-gray-500">Priority {priority}</span>
                )}
              </div>
              {svc && (
                <>
                  <p className="text-xs text-gray-500 mt-0.5 ml-4">{svc.description}</p>
                  {svc.depends_on.length > 0 && (
                    <div className="ml-4 mt-1.5 flex flex-wrap gap-1">
                      {svc.depends_on.map(dep => (
                        <span key={dep} className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded border border-gray-600">
                          ← {dep}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-gray-600 mt-3">
        ← dependency arrows · Priority 0 = recover first
      </p>
    </div>
  );
};
