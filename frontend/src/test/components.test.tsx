import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DependencyPanel } from '../components/DependencyPanel';
import { RecoveryPlanDisplay } from '../components/RecoveryPlan';
import type { RecoveryPlan } from '../types';

describe('DependencyPanel', () => {
  it('renders all services when no affected services provided', () => {
    render(<DependencyPanel affectedServices={[]} />);
    expect(screen.getByText('PilotFish-Core')).toBeDefined();
    expect(screen.getByText('Identity-Service')).toBeDefined();
  });

  it('shows affected count badge when services are affected', () => {
    render(<DependencyPanel affectedServices={['PilotFish-Core', 'PilotFish-API']} />);
    expect(screen.getByText('2 affected')).toBeDefined();
  });
});

describe('RecoveryPlanDisplay', () => {
  const mockPlan: RecoveryPlan = {
    session_id: 'test-session-1',
    summary: 'Test recovery summary',
    affected_services: ['PilotFish-Core'],
    recovery_steps: [
      {
        step_number: 1,
        action: 'Restart Identity-Service',
        rationale: 'Foundation dependency',
        estimated_duration: '2 minutes',
        risk_level: 'LOW',
        dependencies: [],
        verification: 'GET /health returns 200',
      },
    ],
    warnings: ['Test warning message'],
    estimated_total_rto: '15 minutes',
    knowledge_sources: ['pilotfish_recovery_tsg.json'],
  };

  it('renders recovery plan summary', () => {
    render(<RecoveryPlanDisplay plan={mockPlan} />);
    expect(screen.getByText('Test recovery summary')).toBeDefined();
  });

  it('renders recovery steps', () => {
    render(<RecoveryPlanDisplay plan={mockPlan} />);
    expect(screen.getByText('Restart Identity-Service')).toBeDefined();
  });

  it('renders warnings', () => {
    render(<RecoveryPlanDisplay plan={mockPlan} />);
    expect(screen.getByText('Test warning message')).toBeDefined();
  });

  it('renders estimated RTO', () => {
    render(<RecoveryPlanDisplay plan={mockPlan} />);
    expect(screen.getByText('15 minutes')).toBeDefined();
  });
});
