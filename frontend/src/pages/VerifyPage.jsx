import React, { useState, useEffect } from 'react';
import {
  CheckCircle, XCircle, AlertTriangle, Play, Loader,
  Bot, Cpu, Users, ChevronRight, Info
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getApplications, getApplication, getDocuments, runVerification, runAgenticVerification } from '../services/api';
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
  const [checking, setChecking] = useState(false);

  // Readiness state
  const [readiness, setReadiness] = useState({
    applicationCreated: false,
    documentsUploaded: false,
    ocrCompleted: false,
    nlpCompleted: false,
    panAadhaarExtracted: false,
    aadhaarVerification: false,
    panVerification: false,
    screenshotUploaded: false,
    siteVerification: false,
  });

  // Load applications list
  useEffect(() => { getApplications().then((r) => setApps(r.data)).catch(() => {}); }, []);

  // Check readiness when appId changes
  useEffect(() => {
    if (!appId) {
      setReadiness({
        applicationCreated: false,
        documentsUploaded: false,
        ocrCompleted: false,
        nlpCompleted: false,
        panAadhaarExtracted: false,
        aadhaarVerification: false,
        panVerification: false,
        screenshotUploaded: false,
        siteVerification: false,
      });
      return;
    }

    setChecking(true);
    Promise.all([
      getApplication(appId),
      getDocuments(appId),
    ])
    .then(([appRes, docsRes]) => {
      const app = appRes.data;
      const docs = docsRes.data || [];

      // Logic for documents (require at least aadhaar and pan)
      const hasAadhaar = docs.some(d => d.document_type === 'aadhaar');
      const hasPan = docs.some(d => d.document_type === 'pan');
      const documentsUploaded = hasAadhaar && hasPan;

      // OCR & NLP logic for mandatory docs
      const mandatoryDocs = docs.filter(d => ['aadhaar', 'pan'].includes(d.document_type));
      let ocrCompleted = false;
      let nlpCompleted = false;
      if (mandatoryDocs.length > 0) {
        ocrCompleted = mandatoryDocs.every(d => d.extracted_text && d.extracted_text.trim() !== '');
        nlpCompleted = mandatoryDocs.every(d => d.structured_data && d.structured_data.trim() !== '');
      }

      // Extracted PAN & Aadhaar numbers from structured data
      let extractedPan = false;
      let extractedAadhaar = false;
      docs.forEach(d => {
        if (d.structured_data) {
          try {
            const sd = JSON.parse(d.structured_data);
            if (sd.pan_number) extractedPan = true;
            if (sd.aadhaar_number) extractedAadhaar = true;
          } catch (e) {
            // ignore JSON error
          }
        }
      });
      const panAadhaarExtracted = extractedPan && extractedAadhaar;

      // Gov Verification logic — V3: requires BOTH steps
      const govVer = app.gov_verification;
      const aadhaarVerification = govVer ? (govVer.aadhaar_validity_status && govVer.aadhaar_validity_status !== 'Pending') : false;
      const panVerification = govVer ? (govVer.pan_aadhaar_link_status && govVer.pan_aadhaar_link_status !== 'Pending') : false;
      const screenshotUploaded = govVer ? (!!govVer.aadhaar_screenshot_path || !!govVer.screenshot_path) : false;

      // Site verification images logic
      const hasSiteImage = docs.some(d => d.document_type.startsWith('geo_site_'));
      const siteVerification = hasSiteImage;

      setReadiness({
        applicationCreated: !!app,
        documentsUploaded,
        ocrCompleted,
        nlpCompleted,
        panAadhaarExtracted,
        aadhaarVerification,
        panVerification,
        screenshotUploaded,
        siteVerification,
      });
    })
    .catch(err => {
      console.error("Error checking readiness", err);
    })
    .finally(() => {
      setChecking(false);
    });
  }, [appId]);

  const isReady = Object.values(readiness).every(Boolean);
  const completedCount = Object.values(readiness).filter(Boolean).length;
  const totalChecks = Object.keys(readiness).length;

  const handleVerify = async () => {
    if (!appId) return toast.error('Select an application first');
    if (!isReady) return toast.error('Please complete all verification readiness steps first.');
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

  const ChecklistItem = ({ passed, label, tooltip }) => (
    <div className={`flex items-center gap-3 p-2 rounded-lg transition-colors group relative cursor-help
        ${passed ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}
         title={tooltip}>
      {passed ? (
        <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
      ) : (
        <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
      )}
      <span className="font-medium text-sm flex-1">
        {!passed && '❌ Missing: '} {label}
      </span>
      {!passed && (
        <Info className="w-4 h-4 text-red-400 opacity-50 group-hover:opacity-100 transition-opacity" />
      )}
    </div>
  );

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

        {/* Verification Readiness Checklist */}
        {appId && (
          <div className="border border-slate-200 rounded-xl overflow-hidden mt-6">
            <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-bold text-slate-700">Verification Readiness</h3>
              <span className={`text-sm font-semibold px-2.5 py-1 rounded-full ${isReady ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'}`}>
                {checking ? <Loader className="w-4 h-4 animate-spin" /> : `${completedCount} / ${totalChecks} Complete`}
              </span>
            </div>
            
            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <ChecklistItem passed={readiness.applicationCreated} label="Application Created" tooltip="An application profile must be initialized." />
              <ChecklistItem passed={readiness.documentsUploaded} label="Required Documents Uploaded" tooltip="Aadhaar and PAN documents are mandatory." />
              <ChecklistItem passed={readiness.ocrCompleted} label="OCR Completed" tooltip="Extracted text is required for mandatory documents." />
              <ChecklistItem passed={readiness.nlpCompleted} label="NLP Extraction Completed" tooltip="Structured data must be extracted via NLP." />
              <ChecklistItem passed={readiness.panAadhaarExtracted} label="PAN & Aadhaar Extracted" tooltip="Both PAN and Aadhaar numbers must be extracted by the NLP pipeline." />
              <ChecklistItem passed={readiness.aadhaarVerification} label="Aadhaar Validity Verified (UIDAI)" tooltip="Step 1: Aadhaar validity must be checked via UIDAI portal." />
              <ChecklistItem passed={readiness.panVerification} label="PAN–Aadhaar Link Verified" tooltip="Step 2: PAN-Aadhaar linkage must be verified on Income Tax portal." />
              <ChecklistItem passed={readiness.screenshotUploaded} label="Verification Screenshots Uploaded" tooltip="Screenshots from the portals must be attached." />
              <ChecklistItem passed={readiness.siteVerification} label="Site Verification Completed" tooltip="At least one site image must be uploaded." />
            </div>
            
            {!isReady && !checking && (
              <div className="px-4 py-3 bg-red-50 text-red-700 text-sm font-medium border-t border-red-100 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Complete all required verification steps before running AI verification.
              </div>
            )}
          </div>
        )}

        <button onClick={handleVerify} disabled={loading || !appId || (!isReady && !checking)}
          className={`btn-primary flex items-center gap-2 mt-4 ${(!isReady || checking) ? 'opacity-50 cursor-not-allowed' : ''}`}>
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
                  <span className='flex items-center gap-1 text-emerald-600 text-sm font-medium'>
                    <CheckCircle className='w-4 h-4' /> Clear
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
