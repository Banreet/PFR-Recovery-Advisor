export interface RecoveryStep {
  step_number: number;
  action: string;
  rationale: string;
  estimated_duration: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  dependencies: string[];
  verification: string;
}

export interface RecoveryPlan {
  session_id: string;
  summary: string;
  affected_services: string[];
  recovery_steps: RecoveryStep[];
  warnings: string[];
  estimated_total_rto: string;
  knowledge_sources: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ServiceDependency {
  name: string;
  depends_on: string[];
  recovery_priority: number;
  description: string;
}
