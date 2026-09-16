import React, { useEffect, useState } from 'react';
import { Download, FileText, Bot, Cpu } from 'lucide-react';
import toast from 'react-hot-toast';
import { getApplications, getReport, downloadPDF } from '../services/api';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatDate, formatCurrency } from '../utils/formatters';

export default function ReportsPage() {
  const [apps, setApps]       = useState([]);
  const [reports, setReports] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    getApplications()
      .then(async (r) => {
        const verifiedApps = r.data.filter((a) => a.status !== 'pending');
        setApps(verifiedApps);
        const reportMap = {};
        await Promise.all(
          verifiedApps.map((a) =>
            getReport(a.id)
              .then((rr) => { reportMap[a.id] = rr.data; })
              .catch(() => {})
          )
        );
        setReports(reportMap);
      })
      .catch(() => toast.error('Failed to load reports'))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = (appId) => {
    const toastId = toast.loading('Downloading PDF...');
    downloadPDF(appId)
      .then(res => {
        const blob = new Blob([res.data], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `SmartVerify_Report_${appId}.pdf`;
        a.click();
        URL.revokeObjectURL(blobUrl);
        toast.success('PDF downloaded successfully!', { id: toastId });
      })
      .catch(() => toast.error('PDF download failed. Try regenerating first.', { id: toastId }));
  };

  if (loading) return <LoadingSpinner size='lg' />;

  return (
    <div className='space-y-4 max-w-6xl mx-auto'>
      {apps.length === 0 ? (
        <div className='card text-center py-16'>
          <FileText className='w-12 h-12 text-slate-300 mx-auto mb-3' />
          <p className='text-slate-500'>No verified applications yet.</p>
          <p className='text-sm text-slate-400 mt-1'>Run verification to generate reports.</p>
        </div>
      ) : apps.map((app) => {
        const report = reports[app.id];
        const isExpanded = expandedId === app.id;
        
        return (
          <div key={app.id} className='card p-0 overflow-hidden'>
            <div 
              className='p-5 cursor-pointer hover:bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4'
              onClick={() => setExpandedId(isExpanded ? null : app.id)}
            >
              <div className='flex-1'>
                <div className='flex items-center gap-3 mb-2'>
                  <p className='font-semibold'>#{app.id} – {app.applicant_name || 'Unnamed'}</p>
                  <StatusBadge status={app.status} />
                  {report?.verification_mode && (
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      report.verification_mode === 'agentic' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {report.verification_mode === 'agentic' ? <Bot className='w-3 h-3' /> : <Cpu className='w-3 h-3' />}
                      {report.verification_mode === 'agentic' ? 'Multi-Agent' : 'Rule-Based'}
                    </span>
                  )}
                  {report?.fraud_flag && (
                    <span className='inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 font-medium'>
                      ⚠ Fraud Flag
                    </span>
                  )}
                </div>
                <div className='flex flex-wrap gap-4 text-sm text-slate-500'>
                  <span>Loan: {formatCurrency(app.loan_amount)}</span>
                  <span>Created: {formatDate(app.created_at)}</span>
                  {report && (
                    <>
                      <span className={report.verification_score >= 60 ? 'text-green-600' : 'text-red-600'}>
                        Verification: {report.verification_score}/100
                      </span>
                      <span className={report.risk_score < 40 ? 'text-green-600' : 'text-red-600'}>
                        Risk: {report.risk_score}/100
                      </span>
                    </>
                  )}
                </div>
                {report?.agent_summary && !isExpanded && (
                  <p className='text-sm text-slate-600 mt-2 italic truncate'>"{report.agent_summary}"</p>
                )}
              </div>
              <div className='flex items-center gap-3'>
                {report?.pdf_path && (
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDownload(app.id); }}
                    className='btn-primary flex items-center gap-2 whitespace-nowrap'
                  >
                    <Download className='w-4 h-4' /> Download PDF
                  </button>
                )}
                <span className='text-slate-400 text-sm'>{isExpanded ? 'Collapse' : 'Expand'}</span>
              </div>
            </div>

            {isExpanded && (
              <div className='p-5 border-t border-slate-100 bg-slate-50/50 space-y-6'>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div className='card bg-white'>
                    <h3 className='font-semibold text-slate-800 mb-3 border-b pb-2'>Applicant Details</h3>
                    <p className='text-sm text-slate-500 italic'>Details extracted from documents will appear here...</p>
                  </div>
                  <div className='card bg-white'>
                    <h3 className='font-semibold text-slate-800 mb-3 border-b pb-2'>Joint Applicants</h3>
                    <p className='text-sm text-slate-500 italic'>Joint applicant details will appear here...</p>
                  </div>
                  <div className='card bg-white'>
                    <h3 className='font-semibold text-slate-800 mb-3 border-b pb-2'>Loan Details</h3>
                    <ul className='text-sm space-y-2'>
                      <li><span className='text-slate-500'>Branch:</span> {app.branch}</li>
                      <li><span className='text-slate-500'>Type:</span> {app.loan_type}</li>
                      <li><span className='text-slate-500'>Amount:</span> {formatCurrency(app.loan_amount)}</li>
                      <li><span className='text-slate-500'>Tenure:</span> {app.loan_tenure} months</li>
                      <li><span className='text-slate-500'>Interest:</span> {app.interest_rate ? `${app.interest_rate}%` : 'N/A'}</li>
                    </ul>
                  </div>
                  <div className='card bg-white'>
                    <h3 className='font-semibold text-slate-800 mb-3 border-b pb-2'>Property Details</h3>
                    <p className='text-sm text-slate-500 italic'>Property analysis details will appear here...</p>
                  </div>
                </div>
                
                <div className='card bg-white'>
                    <h3 className='font-semibold text-slate-800 mb-3 border-b pb-2'>Site Verification & Officer Remarks</h3>
                    {app.site_verification ? (
                        <ul className='text-sm space-y-2'>
                            <li><span className='text-slate-500'>Officer Name:</span> {app.site_verification.officer_name}</li>
                            <li><span className='text-slate-500'>Date:</span> {formatDate(app.site_verification.visit_date)}</li>
                            <li><span className='text-slate-500'>Condition:</span> {app.site_verification.property_condition}</li>
                            <li><span className='text-slate-500'>Remarks:</span> {app.site_verification.remarks}</li>
                        </ul>
                    ) : (
                        <p className='text-sm text-slate-500 italic'>No site verification details recorded yet.</p>
                    )}
                </div>

                {report?.agent_summary && (
                  <div className='card bg-white border-l-4 border-purple-400'>
                    <h3 className='font-semibold text-purple-800 mb-2'>AI Compliance Summary</h3>
                    <p className='text-sm text-slate-700 leading-relaxed'>{report.agent_summary}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
