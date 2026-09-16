
# write_verify.py
import os

content = '''
import React, { useState, useEffect } from 'react';
import {
  CheckCircle, XCircle, AlertTriangle, Play, Loader,
  Bot, Cpu, Users, ChevronRight
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getApplications, runVerification, runAgenticVerification } from '../services/api';
import ScoreGauge from '../components/ui/ScoreGauge';
import StatusBadge from '../components/ui/StatusBadge';

const AGENT_PIPELINE = [
  { key: 'document_analyst',      label: 'Agent 1',  full: 'Document Analyst',       desc: 'OCR + classification' },
  { key: 'extraction_specialist', label: 'Agent 2',  full: 'Extraction Specialist',  desc: 'NLP information extraction' },
  { key: 'verification_officer',  label: 'Agent 3',  full: 'Verification Officer',    desc: 'Eligibility & identity rules' },
  { key: 'fraud_investigator',    label: 'Agent 4',  full: 'Fraud Investigator',      desc: 'Risk scoring & alerts' },
  { key: 'compliance_reporter',   label: 'Agent 5',  full: 'Compliance Reporter',     desc: 'Final decision & PDF report' },
];

export default function VerifyPage() {
  const [apps, setApps]       = useState([]);
  const [appId, setAppId]     = useState('');
  const [mode, setMode]       = useState('rule_based');
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { getApplications().then((r) => setApps(r.data)).catch(() => {}); }, []);

  const handleVerify = async () => {
    if (!appId) return toast.error('Select an application first');
    setLoading(true);
    setResult(null);
    try {
      const { data } = mode === 'agentic'
        ? await runAgenticVerification(appId)
        : await runVerification(appId);
      setResult(data);
      toast.success(mode === 'agentic' ? 'Multi-agent verification complete!' : 'Verification complete!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed');
    } finally { setLoading(false); }
  };

  return (
    <div className='max-w-4xl mx-auto space-y-6'>
      {/* Controls */}
      <div className='card space-y-5'>
        <div>
          <label className='block text-sm font-medium text-slate-700 mb-1'>Select Application</label>
          <select value={appId} onChange={(e) => { setAppId(e.target.value); setResult(null); }} className='input max-w-md'>
            <option value=''>— Choose application —</option>
            {apps.map((a) => (
              <option key={a.id} value={a.id}>
                #{a.id} — {a.branch || 'Unknown Branch'} | {a.loan_type || '—'} | ₹{Number(a.loan_amount).toLocaleString('en-IN')}
              </option>
            ))}
          </select>
        </div>

        {/* Mode selection */}
        <div>
          <label className='block text-sm font-medium text-slate-700 mb-2'>Verification Mode</label>
          <div className='flex flex-col sm:flex-row gap-3'>
            <button type='button' onClick={() => setMode('rule_based')}
              className={`flex-1 flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all ${mode === 'rule_based' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300 bg-white'}`}>
              <Cpu className={`w-5 h-5 mt-0.5 flex-shrink-0 ${mode === 'rule_based' ? 'text-blue-600' : 'text-slate-400'}`} />
              <div>
                <p className='text-sm font-semibold text-slate-800'>Rule-Based Pipeline</p>
                <p className='text-xs text-slate-500 mt-0.5'>Fast, deterministic. OCR → NLP → rules → fraud checks → PDF.</p>
              </div>
            </button>
            <button type='button' onClick={() => setMode('agentic')}
              className={`flex-1 flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all ${mode === 'agentic' ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:border-slate-300 bg-white'}`}>
              <Users className={`w-5 h-5 mt-0.5 flex-shrink-0 ${mode === 'agentic' ? 'text-purple-600' : 'text-slate-400'}`} />
              <div>
                <p className='text-sm font-semibold text-slate-800 flex items-center gap-2'>
                  Multi-Agent (CrewAI) <Bot className='w-3.5 h-3.5 text-purple-500' />
                </p>
                <p className='text-xs text-slate-500 mt-0.5'>5 specialised AI agents collaborate and explain their decisions.</p>
              </div>
            </button>
          </div>
        </div>

        {/* Agent pipeline display */}
        {mode === 'agentic' && (
          <div>
            <p className='text-xs font-medium text-slate-500 uppercase tracking-wide mb-2'>Agent Pipeline</p>
            <div className='flex flex-wrap items-center gap-1'>
              {AGENT_PIPELINE.map((agent, i) => (
                <React.Fragment key={agent.key}>
                  <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${loading ? 'bg-purple-50 border-purple-200 text-purple-700 animate-pulse' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                    title={`${agent.full}: ${agent.desc}`}>
                    <Bot className='w-3 h-3' />
                    <span className='font-bold'>{agent.label}</span>
                    <span className='hidden sm:inline text-slate-400'>– {agent.full}</span>
                  </div>
                  {i < AGENT_PIPELINE.length - 1 && <ChevronRight className='w-3 h-3 text-slate-300' />}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        <button onClick={handleVerify} disabled={loading || !appId}
          className='btn-primary flex items-center gap-2'>
          {loading ? <Loader className='w-4 h-4 animate-spin' /> : <Play className='w-4 h-4' />}
          {loading ? (mode === 'agentic' ? 'Agents working…' : 'Verifying…') : 'Run Verification'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className='space-y-4'>
          {/* Mode badge */}
          {result.verification_mode && (
            <div className='flex items-center gap-2'>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${result.verification_mode === 'agentic' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'}`}>
                {result.verification_mode === 'agentic' ? <Bot className='w-3.5 h-3.5' /> : <Cpu className='w-3.5 h-3.5' />}
                {result.verification_mode === 'agentic' ? 'Multi-Agent (CrewAI)' : 'Rule-Based'}
              </span>
            </div>
          )}

          {/* Agent summary */}
          {result.agent_summary && (
            <div className='card border-l-4 border-purple-400 bg-purple-50/40'>
              <h3 className='font-semibold text-purple-800 mb-2 flex items-center gap-2'>
                <Bot className='w-5 h-5' /> Compliance Reporter Summary
              </h3>
              <p className='text-sm text-slate-700 leading-relaxed'>{result.agent_summary}</p>
            </div>
          )}

          {/* Scores + Status */}
          <div className='card flex flex-wrap items-center justify-between gap-6'>
            <div className='flex gap-8'>
              <ScoreGauge label='Verification' score={result.verification_score} />
              <ScoreGauge label='Risk Score'   score={result.risk_score} />
            </div>
            <div className='space-y-2'>
              <div className='flex items-center gap-2'>
                <span className='text-sm text-slate-500'>Status:</span>
                <StatusBadge status={result.status} />
              </div>
              <div className='flex items-center gap-2'>
                <span className='text-sm text-slate-500'>Fraud Flag:</span>
                {result.fraud_flag ? (
                  <span className='flex items-center gap-1 text-red-600 text-sm font-medium'>
                    <AlertTriangle className='w-4 h-4' /> Flagged
                  </span>
                ) : (
                  <span className='flex items-center gap-1 text-green-600 text-sm font-medium'>
                    <CheckCircle className='w-4 h-4' /> Clear
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Extracted info */}
          {result.extracted_info && (
            <div className='card'>
              <h3 className='font-semibold text-slate-700 mb-3'>Extracted Information</h3>
              <div className='grid grid-cols-2 md:grid-cols-3 gap-3'>
                {Object.entries(result.extracted_info)
                  .filter(([, v]) => v != null)
                  .map(([k, v]) => (
                    <div key={k} className='bg-slate-50 p-3 rounded-lg'>
                      <p className='text-xs text-slate-500 capitalize'>{k.replace(/_/g, ' ')}</p>
                      <p className='text-sm font-medium text-slate-800 truncate'>{String(v)}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Checks */}
          {result.verification_details?.checks && (
            <div className='card'>
              <h3 className='font-semibold text-slate-700 mb-3'>Verification Checks</h3>
              <div className='space-y-2'>
                {result.verification_details.checks.map((c, i) => (
                  <div key={i} className='flex items-start gap-3 p-3 bg-slate-50 rounded-lg'>
                    {c.passed
                      ? <CheckCircle className='w-5 h-5 text-green-500 mt-0.5 flex-shrink-0' />
                      : <XCircle className='w-5 h-5 text-red-500 mt-0.5 flex-shrink-0' />}
                    <div className='flex-1'>
                      <div className='flex justify-between'>
                        <p className='text-sm font-medium'>{c.name}</p>
                        <span className={`text-xs font-bold ${c.score >= 0.7 ? 'text-green-600' : c.score >= 0.4 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {(c.score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className='text-xs text-slate-500 mt-0.5'>{c.details}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fraud alerts */}
          {result.fraud_analysis?.alerts?.length > 0 && (
            <div className='card border-l-4 border-red-400'>
              <h3 className='font-semibold text-red-700 mb-2 flex items-center gap-2'>
                <AlertTriangle className='w-5 h-5' /> Fraud Alerts
              </h3>
              <ul className='space-y-1'>
                {result.fraud_analysis.alerts.map((a, i) => (
                  <li key={i} className='text-sm text-red-600 flex items-start gap-2'>
                    <span className='mt-1'>!</span> {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
'''

os.makedirs('src/pages', exist_ok=True)
with open('src/pages/VerifyPage.jsx', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content.lstrip('\n'))
print('VerifyPage.jsx written')
