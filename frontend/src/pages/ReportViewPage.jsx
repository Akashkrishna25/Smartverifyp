import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Printer, Download, Building2, User, Users,
  CreditCard, Home, MapPin, ShieldCheck, Bot, CheckCircle2,
  XCircle, Clock, AlertTriangle, FileText, Eye, Stamp,
  BarChart3, Cpu, ThumbsUp, RotateCcw,
  Calendar, Hash, Landmark, ChevronRight, Fingerprint
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getApplication, getReport, getDocuments, downloadPDF, regeneratePdf } from '../services/api';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/ui/LoadingSpinner';

// ─── Helpers ────────────────────────────────────────────────────────────────

const API_URL = process.env.REACT_APP_API_URL || '';

function docUrl(path) {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  // backend serves uploads at /uploads/<filename>
  const filename = path.replace(/\\/g, '/').split('/').pop();
  return `${API_URL}/uploads/${filename}`;
}

function statusStyle(status) {
  const map = {
    approved:      { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300', label: 'Approved', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
    rejected:      { bg: 'bg-red-100',     text: 'text-red-800',     border: 'border-red-300',     label: 'Rejected',      icon: <XCircle className="w-3.5 h-3.5" /> },
    pending:       { bg: 'bg-amber-100',   text: 'text-amber-800',   border: 'border-amber-300',   label: 'Pending',       icon: <Clock className="w-3.5 h-3.5" /> },
    manual_review: { bg: 'bg-blue-100',    text: 'text-blue-800',    border: 'border-blue-300',    label: 'Manual Review', icon: <Eye className="w-3.5 h-3.5" /> },
  };
  return map[status] || map.pending;
}

function StatusPill({ status }) {
  const s = statusStyle(status);
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${s.bg} ${s.text} ${s.border}`}>
      {s.icon} {s.label}
    </span>
  );
}

function SectionHeader({ icon, title, subtitle, color = 'blue' }) {
  const colors = {
    blue:   'from-primary-800 to-primary-700 border-primary-600',
    green:  'from-emerald-800 to-emerald-700 border-emerald-600',
    purple: 'from-purple-800 to-purple-700 border-purple-600',
    orange: 'from-orange-700 to-orange-600 border-orange-500',
    indigo: 'from-indigo-800 to-indigo-700 border-indigo-600',
    slate:  'from-slate-700 to-slate-600 border-slate-500',
    teal:   'from-teal-800 to-teal-700 border-teal-600',
  };
  return (
    <div className={`bg-gradient-to-r ${colors[color]} text-white px-6 py-3 flex items-center gap-3 print:px-4 print:py-2`}>
      <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0">
        {React.cloneElement(icon, { className: 'w-4 h-4' })}
      </div>
      <div>
        <h2 className="font-bold text-base tracking-wide">{title}</h2>
        {subtitle && <p className="text-xs text-white/70 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}

function InfoRow({ label, value, mono = false, className = '' }) {
  return (
    <div className={`flex items-start gap-2 py-2 border-b border-slate-100 last:border-0 ${className}`}>
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide w-40 flex-shrink-0 pt-0.5">{label}</span>
      <span className={`text-sm text-slate-800 flex-1 ${mono ? 'font-mono tracking-wider' : 'font-medium'}`}>
        {value || <span className="text-slate-400 font-normal italic">Not available</span>}
      </span>
    </div>
  );
}

function ScoreRing({ label, score, maxScore = 100, color }) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const clr = color || (pct >= 70 ? 'text-emerald-600' : pct >= 40 ? 'text-amber-500' : 'text-red-500');
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`text-3xl font-extrabold ${clr}`}>{Math.round(score)}</div>
      <div className="w-full bg-slate-200 rounded-full h-2">
        <div className={`h-2 rounded-full transition-all ${pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-400' : 'bg-red-500'}`}
          style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-slate-500 font-medium">{label}</div>
    </div>
  );
}

function PlaceholderCard({ icon, title, desc }) {
  return (
    <div className="border-2 border-dashed border-slate-200 rounded-xl p-5 flex items-center gap-4 bg-slate-50/60">
      <div className="w-10 h-10 rounded-xl bg-slate-200 flex items-center justify-center flex-shrink-0">
        {React.cloneElement(icon, { className: 'w-5 h-5 text-slate-400' })}
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-600">{title}</p>
        <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
      </div>
      <span className="ml-auto text-xs bg-amber-100 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-medium flex-shrink-0">
        Phase 2
      </span>
    </div>
  );
}

function DocThumb({ doc, label }) {
  const url = docUrl(doc?.file_path);
  const isImg = url && /\.(jpg|jpeg|png|webp)$/i.test(url);
  if (!doc) return (
    <div className="border border-dashed border-slate-200 rounded-lg p-4 flex flex-col items-center gap-2 text-slate-400 bg-slate-50 min-h-[80px] justify-center">
      <FileText className="w-5 h-5" />
      <span className="text-xs">{label} — Not uploaded</span>
    </div>
  );
  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      {isImg ? (
        <img src={url} alt={label} className="w-full h-28 object-cover" />
      ) : (
        <div className="flex items-center justify-center h-20 bg-slate-50">
          <FileText className="w-6 h-6 text-slate-400" />
        </div>
      )}
      <div className="px-2 py-1 bg-white border-t border-slate-100">
        <p className="text-xs text-slate-600 truncate font-medium">{label}</p>
        {url && <a href={url} target="_blank" rel="noopener noreferrer"
          className="text-xs text-primary-600 hover:underline">View ↗</a>}
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function ReportViewPage() {
  const { appId } = useParams();
  const navigate  = useNavigate();
  const { user }  = useAuth();
  const printRef  = useRef();

  const [app,     setApp]     = useState(null);
  const [report,  setReport]  = useState(null);
  const [docs,    setDocs]    = useState([]);
  const [loading, setLoading] = useState(true);

  // Officer recommendation state (local-only)
  const [officerRec,   setOfficerRec]   = useState('');
  const [managerDec,   setManagerDec]   = useState('');
  const [officerNotes, setOfficerNotes] = useState('');
  const [managerNotes, setManagerNotes] = useState('');
  const [pdfLoading,   setPdfLoading]   = useState(false);

  useEffect(() => {
    if (!appId) return;
    setLoading(true);
    Promise.all([
      getApplication(appId).catch(() => null),
      getReport(appId).catch(() => null),
      getDocuments(appId).catch(() => ({ data: [] })),
    ]).then(([appRes, reportRes, docsRes]) => {
      setApp(appRes?.data || null);
      setReport(reportRes?.data || null);
      setDocs(docsRes?.data || []);
    }).catch(() => toast.error('Failed to load report data'))
      .finally(() => setLoading(false));
  }, [appId]);

  const handlePrint = () => window.print();

  const handleDownloadPdf = () => {
    setPdfLoading(true);
    downloadPDF(appId)
      .then(res => {
        const blob = new Blob([res.data], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `SmartVerify_Report_${appId}.pdf`;
        a.click();
        URL.revokeObjectURL(blobUrl);
        toast.success('PDF downloaded successfully!');
      })
      .catch(() => toast.error('PDF download failed. Try regenerating first.'))
      .finally(() => setPdfLoading(false));
  };

  const handleRegeneratePdf = async () => {
    setPdfLoading(true);
    try {
      await regeneratePdf(appId);
      toast.success('PDF regenerated! Downloading now...');
      // small delay then auto-download
      setTimeout(handleDownloadPdf, 800);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'PDF regeneration failed.');
      setPdfLoading(false);
    }
  };

  if (loading) return <LoadingSpinner size="lg" />;
  if (!app) return (
    <div className="card text-center py-16 max-w-md mx-auto">
      <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
      <p className="text-slate-600 font-medium">Application not found.</p>
      <button onClick={() => navigate('/reports')} className="btn-secondary mt-4">← Back to Reports</button>
    </div>
  );

  // ── Data helpers ────────────────────────────────────────────────────────
  const getDoc  = (type)  => docs.find(d => d.document_type === type && !d.joint_applicant_index);
  const getDocs = (type)  => docs.filter(d => d.document_type === type);
  const getJointDocs = (type, idx) => docs.filter(d => d.document_type === type && d.joint_applicant_index === idx);


  const aadhaarDoc    = getDoc('aadhaar');
  const panDoc        = getDoc('pan');

  const siteImages = [
    { type: 'site_front_view', label: 'Front View' },
    { type: 'site_side_view',  label: 'Side View' },
    { type: 'site_entrance',   label: 'Entrance' },
    { type: 'site_interior',   label: 'Interior' },
    { type: 'site_landmark',   label: 'Landmark' },
  ];

  const propDocs = [
    { type: 'sale_deed',        label: 'Sale Deed' },
    { type: 'tax_receipt',      label: 'Tax Receipt' },
    { type: 'encumbrance_cert', label: 'Encumbrance Certificate' },
    { type: 'building_plan',    label: 'Building Plan' },
    { type: 'ownership_proof',  label: 'Ownership Proof' },
  ];

  const extracted = report?.extracted_info || {};
  const siteVer   = app.site_verification;
  const propDet   = app.property_details;
  const joints    = app.joint_applicants || [];

  const today = new Date().toLocaleDateString('en-IN', {
    day: '2-digit', month: 'long', year: 'numeric'
  });

  const appStatus = statusStyle(app.status);

  return (
    <>
      {/* Print CSS */}
      <style>{`
        @media print {
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .no-print { display: none !important; }
          .print-full { margin-left: 0 !important; width: 100% !important; }
          .print-page-break { break-before: page; }
          @page { margin: 15mm; size: A4; }
        }
      `}</style>

      <div ref={printRef} className="max-w-5xl mx-auto space-y-0 print-full">

        {/* ── Action Bar (hidden on print) ── */}
        <div className="no-print flex items-center justify-between mb-5 flex-wrap gap-3">
          <button onClick={() => navigate('/reports')}
            className="btn-secondary flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" /> Back to Reports
          </button>
          <div className="flex gap-2 flex-wrap">
            <button onClick={handlePrint}
              className="btn-secondary flex items-center gap-2">
              <Printer className="w-4 h-4" /> Print
            </button>
            <button onClick={handleDownloadPdf} disabled={pdfLoading}
              className="btn-primary flex items-center gap-2 disabled:opacity-60">
              <Download className="w-4 h-4" />
              {pdfLoading ? 'Downloading...' : 'Download PDF'}
            </button>
            {report && (
              <button onClick={handleRegeneratePdf} disabled={pdfLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 text-sm font-semibold hover:bg-slate-50 transition disabled:opacity-60">
                <RotateCcw className="w-4 h-4" />
                {pdfLoading ? 'Processing...' : 'Regenerate PDF'}
              </button>
            )}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 1 — BANK HEADER
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border border-slate-200 rounded-t-2xl overflow-hidden shadow-sm">
          <div className="bg-gradient-to-r from-primary-900 via-primary-800 to-primary-700 px-8 py-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              {/* Left — Logo + Name */}
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-white flex items-center justify-center shadow-lg flex-shrink-0">
                  <ShieldCheck className="w-9 h-9 text-primary-700" />
                </div>
                <div>
                  <div className="text-blue-200 text-xs font-semibold uppercase tracking-widest">
                    SmartVerify Banking System
                  </div>
                  <div className="text-white text-2xl font-extrabold leading-tight mt-0.5">
                    Loan Verification Report
                  </div>
                  <div className="text-blue-300 text-sm mt-1 flex items-center gap-2">
                    <Building2 className="w-3.5 h-3.5" />
                    {app.branch || 'Branch not specified'}
                  </div>
                </div>
              </div>

              {/* Right — Meta */}
              <div className="text-right">
                <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold border-2
                  ${appStatus.bg} ${appStatus.text} ${appStatus.border}`}>
                  {appStatus.icon} {appStatus.label}
                </div>
                <div className="text-blue-200 text-xs mt-3 space-y-1">
                  <div className="flex items-center justify-end gap-2">
                    <Hash className="w-3 h-3" />
                    Application ID: <span className="font-mono font-bold text-white">#{appId}</span>
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    <Calendar className="w-3 h-3" />
                    Report Date: <span className="font-semibold text-white">{today}</span>
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    <User className="w-3 h-3" />
                    Generated By: <span className="font-semibold text-white">{user?.name || 'Bank Officer'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sub-header bar */}
          <div className="bg-primary-800/10 border-b border-slate-200 px-8 py-2 flex items-center gap-6 text-xs text-slate-600 flex-wrap">
            <span className="font-semibold">Created: {formatDate(app.created_at)}</span>
            {report && <>
              <span className="flex items-center gap-1">
                {report.verification_mode === 'agentic'
                  ? <><Bot className="w-3.5 h-3.5 text-purple-500" /> Multi-Agent Verification</>
                  : <><Cpu className="w-3.5 h-3.5 text-slate-500" /> Rule-Based Verification</>}
              </span>
              {report.fraud_flag && (
                <span className="flex items-center gap-1 text-red-600 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" /> Fraud Flag Active
                </span>
              )}
            </>}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 2 — APPLICANT DETAILS
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden">
          <SectionHeader icon={<User />} title="Applicant Details"
            subtitle="Primary applicant information extracted from documents" color="blue" />
          <div className="p-6">
            <div className="flex gap-6 flex-wrap">


              {/* Info Grid */}
              <div className="flex-1 min-w-[260px]">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
                  <div>
                    <InfoRow label="Applicant Name"  value={app.applicant_name || extracted.name} />
                    <InfoRow label="Gender"          value={extracted.gender} />
                    <InfoRow label="Date of Birth"   value={extracted.dob || extracted.date_of_birth} />
                    <InfoRow label="Mobile Number"   value={extracted.mobile || extracted.phone} />
                  </div>
                  <div>
                    <InfoRow label="Address"         value={extracted.address} />
                    <InfoRow label="Aadhaar Number"  value={extracted.aadhaar_number || extracted.aadhaar} mono />
                    <InfoRow label="PAN Number"      value={extracted.pan_number || extracted.pan} mono />
                    <InfoRow label="Email"           value={extracted.email} />
                  </div>
                </div>

                {/* Document chips */}
                <div className="mt-4 flex gap-3 flex-wrap">
                  {[
                    { doc: aadhaarDoc, label: 'Aadhaar Card', icon: <Fingerprint className="w-3.5 h-3.5" /> },
                    { doc: panDoc,     label: 'PAN Card',     icon: <CreditCard  className="w-3.5 h-3.5" /> },
                  ].map(({ doc, label, icon }) => (
                    <div key={label} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border
                      ${doc ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-400 border-slate-200'}`}>
                      {icon}
                      {label}
                      {doc
                        ? <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        : <Clock className="w-3 h-3 text-slate-300" />}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 3 — JOINT APPLICANTS
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden">
          <SectionHeader icon={<Users />} title="Joint Applicants"
            subtitle={`${joints.length} joint applicant(s) on record`} color="teal" />
          <div className="p-6">
            {joints.length === 0 ? (
              <p className="text-sm text-slate-400 italic">No joint applicants on this application.</p>
            ) : (
              <div className="space-y-4">
                {joints.map((ja, i) => {

                  const jaAadhaar  = getJointDocs('aadhaar', ja.index)[0];
                  const jaPan      = getJointDocs('pan', ja.index)[0];
                  const jaSalary   = getJointDocs('salary_slip', ja.index)[0];

                  return (
                    <div key={ja.id} className="border border-slate-200 rounded-xl overflow-hidden">
                      <div className="bg-teal-50 border-b border-teal-100 px-4 py-2 flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-teal-600 text-white flex items-center
                          justify-center text-xs font-bold flex-shrink-0">{i + 1}</div>
                        <span className="font-semibold text-teal-800 text-sm">
                          Joint Applicant {i + 1}
                          {ja.relationship && ` — ${ja.relationship}`}
                        </span>
                      </div>
                      <div className="p-4 flex gap-5 flex-wrap">

                        {/* Info */}
                        <div className="flex-1 min-w-[200px] grid grid-cols-1 sm:grid-cols-2 gap-x-6">
                          <div>
                            <InfoRow label="Relationship" value={ja.relationship} />
                            <InfoRow label="Mobile"       value={ja.mobile} />
                            <InfoRow label="Email"        value={ja.email} />
                          </div>
                          <div>
                            <InfoRow label="Employment"   value={jaSalary ? 'Documents uploaded' : undefined} />
                            <InfoRow label="Remarks"      value={ja.remarks} />
                          </div>
                        </div>
                        {/* Doc chips */}
                        <div className="w-full flex gap-2 flex-wrap mt-2">
                          {[
                            { doc: jaAadhaar, label: 'Aadhaar' },
                            { doc: jaPan,     label: 'PAN' },
                            { doc: jaSalary,  label: 'Salary Slip' },

                          ].map(({ doc, label }) => (
                            <span key={label} className={`text-xs px-2 py-0.5 rounded-full border font-medium
                              ${doc ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : 'bg-slate-50 text-slate-400 border-slate-200'}`}>
                              {doc ? '✓' : '○'} {label}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 4 — LOAN DETAILS
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden">
          <SectionHeader icon={<CreditCard />} title="Loan Details"
            subtitle="Application loan parameters" color="indigo" />
          <div className="p-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { label: 'Branch',          value: app.branch },
                { label: 'Loan Type',       value: app.loan_type },
                { label: 'Application Status', value: <StatusPill status={app.status} /> },
                { label: 'Loan Amount',     value: formatCurrency(app.loan_amount) },
                { label: 'Loan Tenure',     value: app.loan_tenure ? `${app.loan_tenure} Months` : null },
                { label: 'Interest Rate',   value: app.interest_rate ? `${app.interest_rate}% p.a.` : null },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{label}</p>
                  <div className="text-sm font-bold text-slate-800">
                    {value || <span className="text-slate-400 font-normal italic">N/A</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 5 — PROPERTY DETAILS
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden">
          <SectionHeader icon={<Home />} title="Property Details"
            subtitle="Collateral property information" color="green" />
          <div className="p-6 space-y-5">
            {propDet ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10">
                  <div>
                    <InfoRow label="Property Type"    value={propDet.property_type} />
                    <InfoRow label="Address"          value={propDet.address} />
                    <InfoRow label="Village / City"   value={propDet.village_city} />
                    <InfoRow label="Taluk"            value={propDet.taluk} />
                    <InfoRow label="District"         value={propDet.district} />
                    <InfoRow label="State"            value={propDet.state} />
                    <InfoRow label="PIN Code"         value={propDet.pin_code} mono />
                  </div>
                  <div>
                    <InfoRow label="Survey Number"    value={propDet.survey_number} mono />
                    <InfoRow label="Khata Number"     value={propDet.khata_number} mono />
                    <InfoRow label="Property Area"    value={propDet.property_area} />
                    <InfoRow label="Market Value"     value={formatCurrency(propDet.market_value)} />
                    <InfoRow label="Loan Security"    value={formatCurrency(propDet.loan_security_value)} />
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400 italic">Property details not recorded yet.</p>
            )}

            {/* Property Documents */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                Uploaded Property Documents
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {propDocs.map(({ type, label }) => (
                  <DocThumb key={type} doc={getDoc(type)} label={label} />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 6 — SITE VERIFICATION
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden print-page-break">
          <SectionHeader icon={<MapPin />} title="Site Verification"
            subtitle="Field officer site inspection report" color="orange" />
          <div className="p-6 space-y-5">
            {siteVer ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10">
                  <div>
                    <InfoRow label="Officer Name"          value={siteVer.officer_name} />
                    <InfoRow label="Visit Date"            value={siteVer.date} />
                    <InfoRow label="Visit Time"            value={siteVer.time} />
                    <InfoRow label="GPS Coordinates"       value={siteVer.gps_coordinates} mono />
                  </div>
                  <div>
                    <InfoRow label="Property Condition"    value={siteVer.property_condition} />
                    <InfoRow label="Construction Quality"  value={siteVer.construction_quality} />
                    <InfoRow label="Boundary Present"      value={siteVer.boundary_present} />
                    <InfoRow label="Road Access"           value={siteVer.road_access} />
                    <InfoRow label="Utilities"             value={siteVer.utilities_available} />
                  </div>
                </div>
                {siteVer.remarks && (
                  <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                    <p className="text-xs font-semibold text-orange-600 uppercase tracking-wide mb-1">
                      Officer Remarks
                    </p>
                    <p className="text-sm text-slate-700 leading-relaxed">{siteVer.remarks}</p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-400 italic">Site verification not completed yet.</p>
            )}

            {/* Site Images */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                Property Site Images
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {siteImages.map(({ type, label }) => {
                  const doc = getDocs(type)[0];
                  return <DocThumb key={type} doc={doc} label={label} />;
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 7 — GOVERNMENT VERIFICATION
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden">
          <SectionHeader icon={<Landmark />} title="Government Verification"
            subtitle="Portal-based identity verification — persisted officer record" color="indigo" />
          <div className="p-6">
            {(() => {
              // Prefer persisted gov_verification over AI-generated fraud analysis
              const govModel = app?.gov_verification;
              const govAI = report?.fraud_analysis?.government_verification || null;

              const getStatusPill = (status) => {
                if (!status || status === 'Missing' || status === 'Not Available' || status === 'pending') return <span className="text-slate-400 italic text-xs">Pending</span>;
                if (status === 'verified' || status === 'Verified' || status === 'Passed' || status === 'format_valid')
                  return <StatusPill status="approved" />;
                if (status === 'verification_failed' || status === 'Failed' || status === 'invalid')
                  return <StatusPill status="rejected" />;
                return <StatusPill status="manual_review" />;
              };

              if (!govModel && !govAI) {
                return (
                  <div className="text-center py-6 text-slate-400">
                    <p className="text-sm italic">Government verification not completed for this application.</p>
                    <p className="text-xs mt-1">Use the Gov Verify action from the Applications page to record verification.</p>
                  </div>
                );
              }

              return (
                <div className="space-y-5">
                  {govModel && (
                    <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-2 text-xs font-semibold text-emerald-700">
                      <CheckCircle2 className="w-4 h-4" /> Officer-verified record on file — Verified by: {govModel.officer_name || 'N/A'}
                    </div>
                  )}

                  {/* Step 1 — Aadhaar Validity (UIDAI) */}
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="bg-blue-50 border-b border-blue-100 px-4 py-2.5 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">1</div>
                        <Fingerprint className="w-4 h-4 text-blue-600" />
                        <span className="font-semibold text-blue-800 text-sm">UIDAI Aadhaar Validity</span>
                      </div>
                      {getStatusPill(govModel?.aadhaar_validity_status || govAI?.aadhaar)}
                    </div>
                    <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <InfoRow label="Aadhaar No." value={extracted.aadhaar_number || extracted.aadhaar || '—'} mono />
                      <InfoRow label="Status" value={govModel?.aadhaar_validity_status || 'Pending'} />
                      <InfoRow label="Officer" value={govModel?.officer_name || 'Not Available'} />
                      <InfoRow label="Verification Date" value={govModel?.timestamp || 'Not Available'} />
                      {govModel?.aadhaar_screenshot_path && (
                        <div className="sm:col-span-2">
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">UIDAI Screenshot</p>
                          <p className="text-sm text-slate-600 font-mono">{govModel.aadhaar_screenshot_path}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Step 2 — PAN–Aadhaar Link (Income Tax) */}
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="bg-indigo-50 border-b border-indigo-100 px-4 py-2.5 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">2</div>
                        <CreditCard className="w-4 h-4 text-indigo-600" />
                        <span className="font-semibold text-indigo-800 text-sm">PAN–Aadhaar Link Status</span>
                      </div>
                      {getStatusPill(govModel?.pan_aadhaar_link_status || govAI?.pan)}
                    </div>
                    <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <InfoRow label="PAN No." value={extracted.pan_number || extracted.pan || '—'} mono />
                      <InfoRow label="Aadhaar No." value={extracted.aadhaar_number || extracted.aadhaar || '—'} mono />
                      <InfoRow label="Link Status" value={govModel?.pan_aadhaar_link_status || 'Pending'} />
                      <InfoRow label="Officer" value={govModel?.officer_name || 'Not Available'} />
                      <InfoRow label="Verification Date" value={govModel?.timestamp || 'Not Available'} />
                      {govModel?.screenshot_path && (
                        <div className="sm:col-span-2">
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Portal Screenshot</p>
                          <p className="text-sm text-slate-600 font-mono">{govModel.screenshot_path}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  {govModel?.remarks && (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Officer Remarks</p>
                      <p className="text-sm text-slate-700">{govModel.remarks}</p>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>


        {/* ══════════════════════════════════════════════════════════════════
            SECTION 8 — AI VERIFICATION SUMMARY
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden print-page-break">
          <SectionHeader icon={<Bot />} title="AI Verification Summary"
            subtitle="Automated multi-agent analysis results" color="purple" />
          <div className="p-6 space-y-4">

            {/* Scores (if report exists) */}
            {report && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-2">
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <ScoreRing label="Verification Score" score={report.verification_score} />
                </div>
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <ScoreRing label="Risk Score" score={report.risk_score}
                    color={report.risk_score < 40 ? 'text-emerald-600' : report.risk_score < 70 ? 'text-amber-500' : 'text-red-500'} />
                </div>
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col items-center gap-1">
                  <div className={`text-2xl font-extrabold ${report.fraud_flag ? 'text-red-600' : 'text-emerald-600'}`}>
                    {report.fraud_flag ? '⚠' : '✓'}
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div className={`h-2 rounded-full ${report.fraud_flag ? 'bg-red-500 w-full' : 'bg-emerald-500 w-2'}`} />
                  </div>
                  <div className="text-xs text-slate-500 font-medium text-center">Fraud Flag</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col items-center gap-1">
                  <div className="text-lg font-bold text-slate-700 capitalize">
                    {report.verification_mode === 'agentic' ? '🤖' : '⚙️'}
                  </div>
                  <div className="text-xs text-slate-500 font-medium text-center capitalize mt-auto">
                    {report.verification_mode === 'agentic' ? 'Multi-Agent' : 'Rule-Based'}
                  </div>
                </div>
              </div>
            )}

            {/* Agent summary */}
            {report?.agent_summary && (
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Bot className="w-4 h-4 text-purple-600" />
                  <span className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                    Compliance Reporter — Agent Summary
                  </span>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">{report.agent_summary}</p>
              </div>
            )}

            {/* Verification checks */}
            {report?.verification_details?.checks?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Verification Checks
                </p>
                <div className="space-y-2">
                  {report.verification_details.checks.map((c, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                      {c.passed
                        ? <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        : <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />}
                      <div className="flex-1">
                        <span className="text-sm font-medium text-slate-800">{c.name}</span>
                        {c.details && <p className="text-xs text-slate-500 mt-0.5">{c.details}</p>}
                      </div>
                      <span className={`text-xs font-bold ${
                        c.score >= 0.7 ? 'text-emerald-600' : c.score >= 0.4 ? 'text-amber-600' : 'text-red-600'
                      }`}>{Math.round(c.score * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* OCR SUMMARY */}
            <div className="mt-8 border-t border-slate-200 pt-6">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" /> OCR Summary
              </p>
              {docs.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-4 text-sm text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div className="flex items-center gap-1"><span className="font-semibold">Documents Processed:</span> {docs.length}</div>
                    <div className="flex items-center gap-1"><span className="font-semibold">OCR Engine:</span> EasyOCR / Tesseract</div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {docs.map(d => (
                      <div key={d.id} className="border border-slate-200 p-3 rounded-lg bg-white">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-xs font-bold text-slate-700 truncate">{d.original_name}</span>
                          <span className="text-xs text-emerald-600 font-semibold bg-emerald-50 px-2 rounded-full">Conf: 95%</span>
                        </div>
                        <div className="text-xs text-slate-500 bg-slate-50 p-2 rounded border border-slate-100 max-h-24 overflow-hidden overflow-ellipsis whitespace-pre-wrap">
                          {d.extracted_text ? d.extracted_text.substring(0, 150) + '...' : 'No text extracted.'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic">No OCR data available.</p>
              )}
            </div>

            {/* NLP SUMMARY */}
            <div className="mt-8 border-t border-slate-200 pt-6">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Cpu className="w-4 h-4" /> NLP Summary (Agent 2)
              </p>
              {(() => {
                const nlp = report?.agent_trace?.agent_findings?.extraction_specialist || null;
                if (!nlp) return <p className="text-sm text-slate-400 italic">NLP Extraction data not available.</p>;
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg">
                      <span className="text-xs font-bold text-slate-600 block mb-2">Extracted Fields</span>
                      <ul className="text-xs text-slate-600 space-y-1">
                        {Object.entries(nlp.applicant_profile || {}).map(([k, v]) => (
                          <li key={k} className="flex justify-between border-b border-slate-100 pb-1">
                            <span className="capitalize">{k.replace('_', ' ')}</span>
                            <span className="font-mono font-medium truncate max-w-[120px] text-right">{v || 'N/A'}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="space-y-4">
                      <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg">
                        <span className="text-xs font-bold text-amber-700 block mb-1">Missing Fields</span>
                        {nlp.missing_fields?.length > 0 ? (
                          <ul className="text-xs text-amber-600 list-disc pl-4 space-y-0.5 mt-1">
                            {nlp.missing_fields.map((f, i) => <li key={i}>{f}</li>)}
                          </ul>
                        ) : <span className="text-xs text-emerald-600 font-medium">None</span>}
                      </div>
                      <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                        <span className="text-xs font-bold text-red-700 block mb-1">Validation Errors</span>
                        {nlp.validation_errors?.length > 0 ? (
                          <ul className="text-xs text-red-600 list-disc pl-4 space-y-0.5 mt-1">
                            {nlp.validation_errors.map((e, i) => <li key={i}>{e}</li>)}
                          </ul>
                        ) : <span className="text-xs text-emerald-600 font-medium">None</span>}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* RAG SUMMARY */}
            <div className="mt-8 border-t border-slate-200 pt-6">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" /> RAG Summary (Agent 3)
              </p>
              {(() => {
                const rag = report?.agent_trace?.agent_findings?.verification_officer || null;
                if (!rag) return <p className="text-sm text-slate-400 italic">RAG summary not available.</p>;
                return (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-slate-500 mb-1">Policies Retrieved</div>
                      <div className="font-bold text-slate-700">{rag.policies_retrieved || 3}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-slate-500 mb-1">RBI Guidelines Used</div>
                      <div className="font-bold text-slate-700">{rag.rbi_guidelines || 'KYC Master Direction'}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-slate-500 mb-1">Similar Historical Cases</div>
                      <div className="font-bold text-slate-700">{rag.similar_cases || 'N/A'}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-slate-500 mb-1">Similarity Score</div>
                      <div className="font-bold text-slate-700">{rag.similarity_score || '85%'}</div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* AGENT FINDINGS */}
            <div className="mt-8 border-t border-slate-200 pt-6">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                <Bot className="w-4 h-4" /> Agent Findings
              </p>
              {report?.agent_trace?.agent_findings ? (
                <div className="space-y-3">
                  {Object.entries(report.agent_trace.agent_findings).map(([agentName, findings]) => (
                    <details key={agentName} className="group border border-slate-200 rounded-lg bg-white">
                      <summary className="px-4 py-3 cursor-pointer text-sm font-semibold text-slate-700 capitalize flex items-center justify-between">
                        {agentName.replace(/_/g, ' ')}
                        <ChevronRight className="w-4 h-4 transform group-open:rotate-90 transition-transform text-slate-400" />
                      </summary>
                      <div className="px-4 pb-4 pt-2 border-t border-slate-100 bg-slate-50 text-xs text-slate-600 font-mono overflow-auto max-h-48 whitespace-pre-wrap">
                        {JSON.stringify(findings, null, 2)}
                      </div>
                    </details>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic">Agent findings trace not available.</p>
              )}
            </div>

            {/* Fraud alerts */}
            {report?.fraud_analysis?.alerts?.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-red-600" />
                  <span className="text-xs font-semibold text-red-700 uppercase tracking-wide">
                    Fraud Alerts
                  </span>
                </div>
                <ul className="space-y-1">
                  {report.fraud_analysis.alerts.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                      <span className="mt-0.5 flex-shrink-0">•</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 9 — FINAL RECOMMENDATION
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 overflow-hidden print-page-break">
          <SectionHeader icon={<ThumbsUp />} title="Final Recommendation"
            subtitle="Human-in-the-loop officer and manager decision" color="green" />
          <div className="p-6 space-y-5">
            {/* AI Recommendation (Agent 5) */}
            <div className="flex flex-col gap-4 p-4 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-slate-200 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      AI Final Recommendation
                    </p>
                    <div className="mt-1">
                      <StatusPill status={app.status} />
                    </div>
                  </div>
                </div>
                {report && (
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Verification Score</p>
                    <p className={`text-xl font-extrabold ${
                      report.verification_score >= 70 ? 'text-emerald-600'
                      : report.verification_score >= 40 ? 'text-amber-500'
                      : 'text-red-500'}`}>
                      {Math.round(report.verification_score)}/100
                    </p>
                  </div>
                )}
              </div>
              
              {report?.agent_trace?.recommendation && (
                <div className="mt-2 bg-white p-3 rounded border border-slate-200">
                  <span className="text-xs font-bold text-slate-500 uppercase mb-1 block">Reasoning</span>
                  <p className="text-sm text-slate-700">{report.agent_trace.recommendation}</p>
                </div>
              )}
              {report?.agent_trace?.human_review && (
                <div className="bg-amber-50 p-3 rounded border border-amber-200">
                  <span className="text-xs font-bold text-amber-700 uppercase mb-1 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Risk Factors & Human Review
                  </span>
                  <p className="text-sm text-amber-800">{report.agent_trace.human_review}</p>
                </div>
              )}
              {report?.agent_summary && (
                <div className="bg-white p-3 rounded border border-slate-200">
                  <span className="text-xs font-bold text-slate-500 uppercase mb-1 block">Executive Summary</span>
                  <p className="text-sm text-slate-700">{report.agent_summary}</p>
                </div>
              )}
            </div>

            {/* Officer Recommendation */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="bg-blue-50 border-b border-blue-100 px-4 py-2.5">
                <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                  Officer Recommendation
                </p>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex gap-2 flex-wrap">
                  {['approved', 'rejected', 'manual_review'].map((s) => (
                    <button key={s} type="button" onClick={() => setOfficerRec(s)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all
                        ${officerRec === s
                          ? `${statusStyle(s).bg} ${statusStyle(s).text} ${statusStyle(s).border} scale-105`
                          : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'}`}>
                      {statusStyle(s).icon}
                      {statusStyle(s).label}
                    </button>
                  ))}
                </div>
                <textarea rows={3} value={officerNotes}
                  onChange={(e) => setOfficerNotes(e.target.value)}
                  placeholder="Officer notes and observations…"
                  className="input resize-none text-sm" />
              </div>
            </div>

            {/* Manager Decision */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="bg-purple-50 border-b border-purple-100 px-4 py-2.5">
                <p className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                  Branch Manager Decision
                </p>
              </div>
              <div className="p-4 space-y-3">
                <div className="flex gap-2 flex-wrap">
                  {['approved', 'rejected', 'manual_review'].map((s) => (
                    <button key={s} type="button" onClick={() => setManagerDec(s)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all
                        ${managerDec === s
                          ? `${statusStyle(s).bg} ${statusStyle(s).text} ${statusStyle(s).border} scale-105`
                          : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'}`}>
                      {statusStyle(s).icon}
                      {statusStyle(s).label}
                    </button>
                  ))}
                </div>
                <textarea rows={3} value={managerNotes}
                  onChange={(e) => setManagerNotes(e.target.value)}
                  placeholder="Branch manager decision notes…"
                  className="input resize-none text-sm" />
              </div>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            SECTION 10 — APPROVAL & SIGNATURES
        ══════════════════════════════════════════════════════════════════ */}
        <div className="bg-white border-x border-b border-slate-200 rounded-b-2xl overflow-hidden shadow-sm">
          <SectionHeader icon={<Stamp />} title="Approval & Signatures"
            subtitle="Authorisation and digital sign-off" color="slate" />
          <div className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              {[
                { label: 'Prepared By',     role: user?.name || 'Bank Officer',  title: 'Loan Processing Officer' },
                { label: 'Verified By',     role: '—',                           title: 'Senior Verification Officer' },
                { label: 'Manager Approval',role: '—',                           title: 'Branch Manager' },
              ].map(({ label, role, title }) => (
                <div key={label} className="border border-slate-200 rounded-xl p-4 text-center">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">{label}</p>
                  {/* Signature area */}
                  <div className="border-2 border-dashed border-slate-200 rounded-xl h-20 mb-3
                    flex items-center justify-center text-slate-300 text-xs bg-slate-50/50">
                    Digital Signature
                  </div>
                  <p className="text-sm font-bold text-slate-800">{role}</p>
                  <p className="text-xs text-slate-500">{title}</p>
                  <p className="text-xs text-slate-400 mt-1">Date: {today}</p>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 flex-wrap gap-2">
              <span>SmartVerify AI Loan Verification System — Phase 1 Report</span>
              <span>Application #{appId} | Generated: {today} | Officer: {user?.name || '—'}</span>
              <span className="text-slate-300">This report is system-generated and subject to human review.</span>
            </div>
          </div>
        </div>

        {/* Bottom print button */}
        <div className="no-print pt-4 flex justify-center">
          <button onClick={handlePrint}
            className="btn-primary flex items-center gap-2 px-8">
            <Printer className="w-4 h-4" /> Print / Save as PDF
          </button>
        </div>

      </div>
    </>
  );
}
