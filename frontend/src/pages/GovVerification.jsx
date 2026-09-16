import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ShieldCheck, ExternalLink, CheckCircle2, XCircle,
  Clock, Eye, User, FileImage, Trash2, ClipboardCheck,
  BadgeInfo, Save, AlertTriangle, Fingerprint,
  CheckCircle, AlertCircle, Loader2
} from 'lucide-react';
import toast from 'react-hot-toast';
import { submitGovVerification, getApplication, getDocuments } from '../services/api';

// ─── Constants ──────────────────────────────────────────────────────────────

const AADHAAR_STATUS_OPTIONS = [
  { value: 'Valid',                  label: 'Valid' },
  { value: 'Invalid',                label: 'Invalid' },
  { value: 'Pending',                label: 'Pending' },
  { value: 'Manual Review Required', label: 'Manual Review Required' },
];

const PAN_STATUS_OPTIONS = [
  { value: 'Linked',                 label: 'Linked' },
  { value: 'Not Linked',             label: 'Not Linked' },
  { value: 'Pending',                label: 'Pending' },
  { value: 'Manual Review Required', label: 'Manual Review Required' },
];

const LINK_UIDAI_PORTAL    = 'https://myaadhaar.uidai.gov.in/check-aadhaar-validity/en';
const LINK_AADHAAR_PORTAL  = 'https://eportal.incometax.gov.in/iec/foservices/#/pre-login/link-aadhaar-status';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function extractFromDocuments(docs) {
  let panNumber     = null;
  let aadhaarNumber = null;
  let applicantName = null;

  const sorted = [...docs].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  const parseSD = (doc) => {
    if (!doc.structured_data) return {};
    try { return JSON.parse(doc.structured_data); }
    catch { return {}; }
  };

  // Priority pass: prefer matching doc type
  for (const doc of sorted) {
    const sd = parseSD(doc);
    if (!panNumber     && doc.document_type === 'pan'     && sd.pan_number)     panNumber     = sd.pan_number;
    if (!aadhaarNumber && doc.document_type === 'aadhaar' && sd.aadhaar_number) aadhaarNumber = sd.aadhaar_number;
    if (!applicantName && sd.applicant_name) applicantName = sd.applicant_name;
  }

  // Fallback pass
  for (const doc of sorted) {
    const sd = parseSD(doc);
    if (!panNumber     && sd.pan_number)     panNumber     = sd.pan_number;
    if (!aadhaarNumber && sd.aadhaar_number) aadhaarNumber = sd.aadhaar_number;
    if (!applicantName && sd.applicant_name) applicantName = sd.applicant_name;
  }

  return {
    panNumber:     panNumber     || null,
    aadhaarNumber: aadhaarNumber || null,
    applicantName: applicantName || null,
    panSource:     panNumber     ? 'ocr' : 'none',
    aadhaarSource: aadhaarNumber ? 'ocr' : 'none',
    nameSource:    applicantName ? 'ocr' : 'none',
  };
}

// ─── Status Config ────────────────────────────────────────────────────────────

function statusConfig(status) {
  switch (status) {
    case 'Valid':
    case 'Linked':
      return {
        badge:  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200',
        dot:    'bg-emerald-500',
        icon:   <CheckCircle2 className="w-3.5 h-3.5" />,
        label:  status,
        ring:   'ring-emerald-300',
        header: 'border-l-4 border-emerald-400',
      };
    case 'Invalid':
    case 'Not Linked':
      return {
        badge:  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 border border-red-200',
        dot:    'bg-red-500',
        icon:   <XCircle className="w-3.5 h-3.5" />,
        label:  status,
        ring:   'ring-red-300',
        header: 'border-l-4 border-red-400',
      };
    case 'Manual Review Required':
      return {
        badge:  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200',
        dot:    'bg-blue-500',
        icon:   <Eye className="w-3.5 h-3.5" />,
        label:  'Manual Review',
        ring:   'ring-blue-300',
        header: 'border-l-4 border-blue-400',
      };
    default:
      return {
        badge:  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 border border-amber-200',
        dot:    'bg-amber-500',
        icon:   <Clock className="w-3.5 h-3.5" />,
        label:  'Pending',
        ring:   'ring-amber-300',
        header: 'border-l-4 border-amber-400',
      };
  }
}

// ─── Extracted Field Display ──────────────────────────────────────────────────

function ExtractedField({ label, value, source, loading, missingText }) {
  if (loading) {
    return (
      <div>
        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
          {label}
        </label>
        <div className="flex items-center gap-2 h-10 bg-slate-50 rounded-xl border border-slate-200 px-3">
          <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
          <span className="text-sm text-slate-400">Loading from OCR…</span>
        </div>
      </div>
    );
  }

  const hasValue = !!value;

  return (
    <div>
      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="text"
          readOnly
          value={hasValue ? value : ''}
          placeholder={missingText || `No ${label} extracted`}
          className={`input font-mono tracking-wider cursor-not-allowed select-all border-slate-200
            ${hasValue
              ? 'bg-white text-slate-800 uppercase'
              : 'bg-slate-50 text-slate-400 placeholder:text-slate-400 placeholder:italic placeholder:font-sans placeholder:tracking-normal'
            }`}
        />
        <div
          className="flex-shrink-0 p-2 rounded-lg bg-white border border-slate-200"
          title="Read-only — auto-extracted by OCR + NLP pipeline"
        >
          <BadgeInfo className="w-4 h-4 text-slate-400" />
        </div>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5">
        {source === 'ocr' ? (
          <>
            <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
            <span className="text-xs text-emerald-600 font-medium">Extracted from OCR</span>
          </>
        ) : (
          <>
            <AlertCircle className="w-3 h-3 text-amber-500 flex-shrink-0" />
            <span className="text-xs text-amber-600">
              Not yet extracted — upload &amp; process document first
            </span>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Screenshot Dropzone ──────────────────────────────────────────────────────

function ScreenshotDropzone({ screenshot, onFileAccepted, onClear, label = 'Upload Verification Screenshot' }) {
  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) onFileAccepted(accepted[0]);
  }, [onFileAccepted]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    multiple: false,
  });

  if (screenshot) {
    return (
      <div className="relative group rounded-xl overflow-hidden border border-slate-200 bg-slate-50">
        {screenshot.name.toLowerCase().endsWith('.pdf') ? (
          <div className="w-full h-44 flex flex-col items-center justify-center text-slate-500">
            <ClipboardCheck className="w-10 h-10 text-primary-500 mb-2" />
            <span className="font-semibold text-sm">{screenshot.name}</span>
          </div>
        ) : (
          <img
            src={screenshot.url}
            alt="Verification screenshot"
            className="w-full h-44 object-cover"
          />
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
          <button
            onClick={(e) => { e.stopPropagation(); onClear(); }}
            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 bg-red-600 text-white text-xs font-medium px-3 py-1.5 rounded-lg"
          >
            <Trash2 className="w-3.5 h-3.5" /> Remove
          </button>
        </div>
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2 pointer-events-none">
          <p className="text-white text-xs truncate">{screenshot.name}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all min-h-[9rem]
        ${isDragActive
          ? 'border-primary-400 bg-primary-50'
          : 'border-slate-300 bg-slate-50 hover:border-primary-400 hover:bg-primary-50/50'
        }`}
    >
      <input {...getInputProps()} />
      <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors
        ${isDragActive ? 'bg-primary-100' : 'bg-slate-100'}`}>
        <FileImage className={`w-5 h-5 ${isDragActive ? 'text-primary-600' : 'text-slate-400'}`} />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-slate-700">
          {isDragActive ? 'Drop screenshot here' : label}
        </p>
        <p className="text-xs text-slate-400 mt-0.5">Drag &amp; drop or click — JPG, PNG, PDF</p>
      </div>
    </div>
  );
}

// ─── Status Button Group ──────────────────────────────────────────────────────

function StatusButtonGroup({ options, currentValue, onChange }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {options.map((opt) => {
        const cfg      = statusConfig(opt.value);
        const isActive = currentValue === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold border-2 transition-all duration-150 text-left
              ${isActive
                ? `${cfg.badge.replace('inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ', '')} border-current shadow-sm`
                : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50'
              }`}
          >
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${isActive ? cfg.dot : 'bg-slate-300'}`} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── Initial State ────────────────────────────────────────────────────────────

const INITIAL_STATE = {
  aadhaarStatus:    'Pending',
  aadhaarScreenshot: null,
  panStatus:        'Pending',
  panScreenshot:    null,
  date:             '',
  time:             '',
  officerName:      '',
  remarks:          '',
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function GovVerificationPage() {
  const { appId }  = useParams();
  const navigate   = useNavigate();
  const [data, setData]         = useState({ ...INITIAL_STATE });
  const [isSaving, setIsSaving] = useState(false);

  // OCR-extracted values
  const [panNumber,     setPanNumber]     = useState(null);
  const [aadhaarNumber, setAadhaarNumber] = useState(null);
  const [applicantName, setApplicantName] = useState(null);
  const [panSource,     setPanSource]     = useState('none');
  const [aadhaarSource, setAadhaarSource] = useState('none');
  const [nameSource,    setNameSource]    = useState('none');
  const [extracting,    setExtracting]   = useState(true);

  // ── Load application + documents on mount ──────────────────────────────
  useEffect(() => {
    if (!appId) return;
    setExtracting(true);
    Promise.all([
      getApplication(appId),
      getDocuments(appId),
    ])
      .then(([appRes, docsRes]) => {
        const appData = appRes.data;

        // Restore saved gov verification state
        const gov = appData.gov_verification;
        if (gov) {
          const parts = gov.timestamp ? gov.timestamp.split(' ') : [];
          setData(prev => ({
            ...prev,
            aadhaarStatus:  gov.aadhaar_validity_status || 'Pending',
            panStatus:      gov.pan_aadhaar_link_status  || 'Pending',
            officerName:    gov.officer_name || '',
            date:           parts[0] || '',
            time:           parts.slice(1).join(' ') || '',
            remarks:        gov.remarks || '',
          }));
        }

        // Applicant name from application record first, then documents
        const appName = appData.applicant_name || null;

        // Extract from documents
        const docs      = docsRes.data || [];
        const extracted = extractFromDocuments(docs);
        setPanNumber(extracted.panNumber);
        setAadhaarNumber(extracted.aadhaarNumber);
        setApplicantName(appName || extracted.applicantName);
        setPanSource(extracted.panSource);
        setAadhaarSource(extracted.aadhaarSource);
        setNameSource(appName ? 'ocr' : extracted.nameSource);
      })
      .catch(err => {
        console.error('Error loading gov verification data', err);
        toast.error('Could not load application data');
      })
      .finally(() => setExtracting(false));
  }, [appId]);

  const patchData = (patch) => setData(prev => ({ ...prev, ...patch }));

  // ── Aadhaar handlers ───────────────────────────────────────────────────
  const handleAadhaarStatusChange = (newStatus) => {
    if (newStatus === 'Valid' && !data.aadhaarScreenshot) {
      toast.error('Upload the UIDAI screenshot before marking as Valid.', { icon: '📸' });
      return;
    }
    const now = new Date();
    patchData({
      aadhaarStatus: newStatus,
      date: newStatus !== 'Pending' ? now.toISOString().split('T')[0] : data.date,
      time: newStatus !== 'Pending' ? now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : data.time,
    });
  };

  const handleAadhaarScreenshotAccepted = (file) => {
    const url = URL.createObjectURL(file);
    patchData({ aadhaarScreenshot: { url, name: file.name, size: file.size } });
    toast.success('Aadhaar screenshot uploaded!');
  };

  const handleClearAadhaarScreenshot = () => {
    if (data.aadhaarScreenshot?.url) URL.revokeObjectURL(data.aadhaarScreenshot.url);
    patchData({ aadhaarScreenshot: null });
  };

  // ── PAN handlers ───────────────────────────────────────────────────────
  const handlePanStatusChange = (newStatus) => {
    if (newStatus === 'Linked' && !data.panScreenshot) {
      toast.error('Upload the portal screenshot before marking as Linked.', { icon: '📸' });
      return;
    }
    const now = new Date();
    patchData({
      panStatus: newStatus,
      date: newStatus !== 'Pending' ? now.toISOString().split('T')[0] : data.date,
      time: newStatus !== 'Pending' ? now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : data.time,
    });
  };

  const handlePanScreenshotAccepted = (file) => {
    const url = URL.createObjectURL(file);
    patchData({ panScreenshot: { url, name: file.name, size: file.size } });
    toast.success('PAN screenshot uploaded!');
  };

  const handleClearPanScreenshot = () => {
    if (data.panScreenshot?.url) URL.revokeObjectURL(data.panScreenshot.url);
    patchData({ panScreenshot: null });
  };

  // ── Save ───────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!appId) return toast.error('No Application ID provided');
    if (data.aadhaarStatus === 'Valid' && !data.aadhaarScreenshot) {
      toast.error('Screenshot is mandatory when Aadhaar status is Valid');
      return;
    }
    if (data.panStatus === 'Linked' && !data.panScreenshot) {
      toast.error('Screenshot is mandatory when PAN-Aadhaar status is Linked');
      return;
    }
    setIsSaving(true);
    try {
      const payload = {
        aadhaar_validity_status: data.aadhaarStatus,
        aadhaar_screenshot_path: data.aadhaarScreenshot ? data.aadhaarScreenshot.name : '',
        pan_aadhaar_link_status: data.panStatus,
        tax_receipt_status:      'pending',
        officer_name:            data.officerName,
        timestamp:               data.date && data.time ? `${data.date} ${data.time}` : '',
        remarks:                 data.remarks,
        screenshot_path:         data.panScreenshot ? data.panScreenshot.name : '',
      };
      await submitGovVerification(appId, payload);
      toast.success('Verifications saved successfully!');
      navigate('/applications');
    } catch {
      toast.error('Failed to save verification');
    } finally {
      setIsSaving(false);
    }
  };

  const aadhaarDone = data.aadhaarStatus !== 'Pending';

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20">

      {/* Page Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2.5">
            <ShieldCheck className="w-6 h-6 text-primary-600" />
            GOVERNMENT IDENTITY VERIFICATION
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Two-step verification: UIDAI Aadhaar validity → Income Tax PAN-Aadhaar link.
          </p>
        </div>
        <button
          id="gov-save-btn"
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-5 py-2.5 rounded-xl font-semibold transition-colors disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving…' : 'Save Verifications'}
        </button>
      </div>

      {/* Step connector */}
      <div className="flex items-center gap-3 text-xs font-semibold text-slate-500 px-1">
        <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${aadhaarDone ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
          {aadhaarDone ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
          Step 1: Aadhaar
        </span>
        <div className="flex-1 border-t border-dashed border-slate-300" />
        <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${!aadhaarDone ? 'bg-slate-50 text-slate-400 border-slate-200' : data.panStatus !== 'Pending' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
          {!aadhaarDone ? <Clock className="w-3 h-3" /> : data.panStatus !== 'Pending' ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
          Step 2: PAN–Aadhaar
        </span>
      </div>

      {/* ═══════════════════════════════════════════════════════
          STEP 1 — AADHAAR VALIDITY (UIDAI)
      ═══════════════════════════════════════════════════════ */}
      <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 ${
        data.aadhaarStatus !== 'Pending' ? `ring-2 ${statusConfig(data.aadhaarStatus).ring}` : ''
      }`}>

        {/* Card header */}
        <div className={`px-6 py-4 ${statusConfig(data.aadhaarStatus).header} bg-gradient-to-r from-slate-50 to-white flex items-start justify-between`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-blue-100 flex-shrink-0">
              <span className="text-blue-600 font-extrabold text-lg">1</span>
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-base">Government Aadhaar Verification</h3>
              <p className="text-xs text-slate-500 mt-0.5">Official UIDAI Aadhaar Validity Check</p>
            </div>
          </div>
          <span className={statusConfig(data.aadhaarStatus).badge}>
            {statusConfig(data.aadhaarStatus).icon}
            {statusConfig(data.aadhaarStatus).label}
          </span>
        </div>

        {/* Card body */}
        <div className="px-6 py-6 space-y-5">

          {/* Extracted data (read-only) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 border border-slate-100 p-4 rounded-xl">
            <ExtractedField
              label="Applicant Name"
              value={applicantName}
              source={nameSource}
              loading={extracting}
              missingText="No Aadhaar extracted"
            />
            <ExtractedField
              label="Applicant Aadhaar Number"
              value={aadhaarNumber}
              source={aadhaarSource}
              loading={extracting}
              missingText="No Aadhaar extracted"
            />
          </div>

          {/* Portal Button */}
          <a
            id="uidai-portal-btn"
            href={LINK_UIDAI_PORTAL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-3.5 px-4 rounded-xl font-bold text-[15px] transition-all duration-150 bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg"
          >
            <ExternalLink className="w-5 h-5" />
            Open UIDAI Portal — Check Aadhaar Validity
          </a>

          {/* Screenshot Upload */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              UIDAI Screenshot
              {data.aadhaarStatus === 'Valid' && <span className="text-red-500 ml-1">* Required</span>}
            </label>
            <ScreenshotDropzone
              screenshot={data.aadhaarScreenshot}
              onFileAccepted={handleAadhaarScreenshotAccepted}
              onClear={handleClearAadhaarScreenshot}
              label="Upload UIDAI Verification Screenshot"
            />
            {data.aadhaarStatus === 'Valid' && !data.aadhaarScreenshot && (
              <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
                <XCircle className="w-3 h-3" /> Screenshot is mandatory for Valid status.
              </p>
            )}
          </div>

          {/* Verification Result */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Aadhaar Verification Result
            </label>
            <StatusButtonGroup
              options={AADHAAR_STATUS_OPTIONS}
              currentValue={data.aadhaarStatus}
              onChange={handleAadhaarStatusChange}
            />
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          STEP 2 — PAN–AADHAAR LINK (Income Tax Portal)
      ═══════════════════════════════════════════════════════ */}
      <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 relative
        ${data.panStatus !== 'Pending' ? `ring-2 ${statusConfig(data.panStatus).ring}` : ''}
      `}>

        {/* Disabled overlay when Step 1 not done */}
        {!aadhaarDone && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-[2px] flex items-center justify-center z-10 rounded-2xl">
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-6 py-4 max-w-xs text-center shadow-sm">
              <AlertTriangle className="w-7 h-7 text-amber-500 mx-auto mb-2" />
              <p className="text-sm font-semibold text-amber-800">Complete Aadhaar Verification before continuing.</p>
              <p className="text-xs text-amber-600 mt-1">Step 1 must be finished first.</p>
            </div>
          </div>
        )}

        {/* Card header */}
        <div className={`px-6 py-4 ${statusConfig(data.panStatus).header} bg-gradient-to-r from-slate-50 to-white flex items-start justify-between`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-indigo-100 flex-shrink-0">
              <span className="text-indigo-600 font-extrabold text-lg">2</span>
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-base">PAN–Aadhaar Link Verification</h3>
              <p className="text-xs text-slate-500 mt-0.5">Official Income Tax Portal Link Status</p>
            </div>
          </div>
          <span className={statusConfig(data.panStatus).badge}>
            {statusConfig(data.panStatus).icon}
            {statusConfig(data.panStatus).label}
          </span>
        </div>

        {/* Card body */}
        <div className="px-6 py-6 space-y-5">

          {/* Extracted data (read-only) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 border border-slate-100 p-4 rounded-xl">
            <ExtractedField
              label="Applicant PAN Number"
              value={panNumber}
              source={panSource}
              loading={extracting}
              missingText="No PAN extracted"
            />
            <ExtractedField
              label="Applicant Aadhaar Number"
              value={aadhaarNumber}
              source={aadhaarSource}
              loading={extracting}
              missingText="No Aadhaar extracted"
            />
          </div>

          {/* Portal Button */}
          <a
            id="incometax-portal-btn"
            href={LINK_AADHAAR_PORTAL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-3.5 px-4 rounded-xl font-bold text-[15px] transition-all duration-150 bg-indigo-600 hover:bg-indigo-700 text-white shadow-md hover:shadow-lg"
          >
            <ExternalLink className="w-5 h-5" />
            Open Income Tax Portal — Check PAN–Aadhaar Link
          </a>

          {/* Screenshot Upload */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Portal Screenshot
              {data.panStatus === 'Linked' && <span className="text-red-500 ml-1">* Required</span>}
            </label>
            <ScreenshotDropzone
              screenshot={data.panScreenshot}
              onFileAccepted={handlePanScreenshotAccepted}
              onClear={handleClearPanScreenshot}
              label="Upload PAN–Aadhaar Link Screenshot"
            />
            {data.panStatus === 'Linked' && !data.panScreenshot && (
              <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
                <XCircle className="w-3 h-3" /> Screenshot is mandatory for Linked status.
              </p>
            )}
          </div>

          {/* Verification Result */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Link Verification Result
            </label>
            <StatusButtonGroup
              options={PAN_STATUS_OPTIONS}
              currentValue={data.panStatus}
              onChange={handlePanStatusChange}
            />
          </div>
        </div>
      </div>

      {/* Officer Details */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 px-6 py-6">
        <h4 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
          <User className="w-4 h-4 text-slate-400" />
          Officer Details
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Officer Name</label>
            <input
              id="gov-officer-name"
              type="text"
              placeholder="e.g. John Doe"
              value={data.officerName}
              onChange={(e) => patchData({ officerName: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Verification Date</label>
            <input
              type="date"
              value={data.date}
              onChange={(e) => patchData({ date: e.target.value })}
              className="input text-slate-700"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Verification Time</label>
            <input
              type="time"
              value={data.time}
              onChange={(e) => patchData({ time: e.target.value })}
              className="input text-slate-700"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Remarks</label>
            <textarea
              rows={2}
              placeholder="Add any additional observations or notes…"
              value={data.remarks}
              onChange={(e) => patchData({ remarks: e.target.value })}
              className="input resize-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
}