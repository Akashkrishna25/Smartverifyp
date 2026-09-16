import React, { useState, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileCheck, AlertCircle, Loader, Plus, X,
  MapPin, Camera, ChevronDown, ChevronUp, User, Briefcase, Home, Image,
  CheckCircle, FileText, AlertTriangle
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  uploadDocument, processDocument, getDocuments,
  getApplications, submitSiteVerification, submitJointApplicant, submitPropertyDetails,
  updateApplicantDetails
} from '../services/api';
import { PROPERTY_CONDITIONS } from '../utils/constants';

// ─── Document sections config ─────────────────────────────────────────────────

const APPLICANT_DOCS = [
  { value: 'aadhaar',         label: 'Aadhaar Card', required: true },
  { value: 'pan',             label: 'PAN Card', required: true },
];

const EMPLOYMENT_DOCS = [
  { value: 'salary_slip',     label: 'Salary Slip' },
  { value: 'form_16',         label: 'Form 16' },
];

const PROPERTY_DOCS = [
  { value: 'sale_deed',          label: 'Sale Deed', required: true },
  { value: 'tax_receipt',        label: 'Tax Receipt', required: true },
  { value: 'encumbrance_cert',   label: 'Encumbrance Certificate', required: true },
  { value: 'building_plan',      label: 'Building Plan' },
  { value: 'ownership_proof',    label: 'Ownership Proof' },
];

const PROPERTY_IMAGES = [
  { value: 'site_front_view',   label: 'Front View' },
  { value: 'site_side_view',    label: 'Side View' },
  { value: 'site_interior',     label: 'Interior' },
  { value: 'site_entrance',     label: 'Entrance' },
  { value: 'site_landmark',     label: 'Landmark' },
];

const JOINT_DOC_TYPES = [
  { value: 'aadhaar',         label: 'Aadhaar Card' },
  { value: 'pan',             label: 'PAN Card' },
  { value: 'salary_slip',     label: 'Salary Slip' },
];

// ─── Dropzone helper ──────────────────────────────────────────────────────────

function DocDropzone({ label, docType, applicationId, jointIndex, existingDoc, onUploaded }) {
  const [file, setFile]         = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [replacing, setReplacing] = useState(false);

  useEffect(() => {
    if (file && file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [file]);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg','.jpeg','.png'], 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    let docId = null;

    // Phase 1: Upload Document
    try {
      const fd = new FormData();
      fd.append('application_id', applicationId);
      fd.append('document_type', docType);
      if (jointIndex !== undefined) fd.append('joint_applicant_index', jointIndex);
      fd.append('file', file);
      
      const { data: doc } = await uploadDocument(fd);
      docId = doc.id;
      
      // Upload succeeded! Update UI immediately
      setFile(null);
      setReplacing(false);
      toast.success(`${label} uploaded successfully!`);
      if (onUploaded) onUploaded();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to upload ${label}`);
      setUploading(false);
      return; // Stop here if upload itself fails
    }

    // Phase 2: Process Document
    try {
      await processDocument(docId);
      toast.success(`${label} processed successfully!`);
      if (onUploaded) onUploaded(); // Refresh data to show extracted info
    } catch (err) {
      toast.error(`Document uploaded successfully, but processing failed: ${err.response?.data?.detail || err.message}`);
    } finally { 
      setUploading(false); 
    }
  };

  if (existingDoc && !replacing) {
    return (
      <div className='flex flex-col gap-2 p-3 bg-green-50/50 border border-green-200 rounded-lg h-full'>
        <p className='text-sm font-medium text-slate-700'>{label}</p>
        <div className='flex items-center gap-2 mt-auto'>
          <FileCheck className='w-5 h-5 text-green-500 flex-shrink-0' />
          <span className='text-xs font-medium text-green-700 truncate' title={existingDoc.original_name}>
            {existingDoc.original_name || 'Uploaded'}
          </span>
          <button onClick={() => setReplacing(true)} className='ml-auto text-xs text-blue-600 hover:text-blue-800 font-medium underline flex-shrink-0'>
            Replace
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className='space-y-2 flex flex-col h-full'>
      <div className='flex justify-between items-center'>
        <p className='text-sm font-medium text-slate-700'>{label}</p>
        {existingDoc && replacing && (
          <button onClick={() => { setReplacing(false); setFile(null); }} className='text-xs text-slate-500 hover:text-slate-700 underline'>
            Cancel
          </button>
        )}
      </div>
      
      <div {...getRootProps()} className={`flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-300 hover:border-blue-400'}`}>
        <input {...getInputProps()} />
        {file ? (
           previewUrl ? (
             <div className="flex flex-col items-center gap-2 w-full">
               <img src={previewUrl} alt="Preview" className="h-20 w-auto object-cover rounded shadow-sm border border-slate-200" />
               <p className='text-xs text-blue-700 font-medium truncate w-full'>{file.name}</p>
             </div>
           ) : (
             <div className="flex flex-col items-center gap-2 w-full">
               <FileText className="h-10 w-10 text-blue-500" />
               <p className='text-xs text-blue-700 font-medium truncate w-full'>{file.name}</p>
             </div>
           )
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-6 w-6 text-slate-400" />
            <p className='text-xs text-slate-500'>{isDragActive ? 'Drop here' : 'Drag & drop or click to browse'}</p>
            <p className='text-[10px] text-slate-400'>PDF, JPG, PNG up to 20MB</p>
          </div>
        )}
      </div>
      
      {file && (
        <div className='flex gap-2 mt-2'>
          <button onClick={handleUpload} disabled={uploading}
            className='btn-primary flex-1 flex items-center justify-center gap-1 text-xs py-1.5'>
            {uploading ? <Loader className='w-3 h-3 animate-spin' /> : <Upload className='w-3 h-3' />}
            {uploading ? 'Processing…' : 'Upload'}
          </button>
          <button onClick={() => setFile(null)} disabled={uploading} className='p-1.5 text-slate-400 hover:text-slate-600 bg-slate-100 rounded hover:bg-slate-200 transition-colors'>
            <X className='w-4 h-4' />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ icon: Icon, title, color = 'blue', children }) {
  const [open, setOpen] = useState(true);
  const colors = {
    blue:   'bg-blue-600',
    green:  'bg-green-600',
    purple: 'bg-purple-600',
    orange: 'bg-orange-500',
    teal:   'bg-teal-600',
    indigo: 'bg-indigo-600',
  };
  return (
    <div className='card overflow-hidden p-0 shadow-sm rounded-xl'>
      <button onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center gap-3 px-5 py-4 text-white ${colors[color]} hover:opacity-90 transition-opacity`}>
        <Icon className='w-5 h-5 flex-shrink-0' />
        <span className='font-semibold text-sm flex-1 text-left'>{title}</span>
        {open ? <ChevronUp className='w-4 h-4' /> : <ChevronDown className='w-4 h-4' />}
      </button>
      {open && <div className='p-5'>{children}</div>}
    </div>
  );
}

// ─── Joint Applicant ──────────────────────────────────────────────────────────

function JointApplicantCard({ index, applicationId, onRemove, uploadedDocs, onUploaded }) {
  const [open, setOpen] = useState(true);
  const [formData, setFormData] = useState({
    relationship: '', mobile: '', email: '', remarks: ''
  });
  const [saving, setSaving] = useState(false);

  const getDoc = (dt) => uploadedDocs.find(d => d.document_type === dt && d.joint_applicant_index === index);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await submitJointApplicant(applicationId, { index, ...formData });
      toast.success(`Joint Applicant ${index} details saved!`);
    } catch (err) {
      toast.error('Failed to save details');
    } finally {
      setSaving(false);
    }
  };

  const missingDocs = JOINT_DOC_TYPES.filter(dt => !getDoc(dt.value));
  const completedDocs = JOINT_DOC_TYPES.filter(dt => getDoc(dt.value));

  return (
    <div className='border border-slate-200 rounded-xl overflow-hidden shadow-sm'>
      <div className='flex items-center justify-between p-4 bg-slate-50 border-b border-slate-200 cursor-pointer' onClick={() => setOpen(!open)}>
        <h4 className='font-semibold text-slate-700 text-sm flex items-center gap-2'>
          {open ? <ChevronUp className='w-4 h-4' /> : <ChevronDown className='w-4 h-4' />}
          <User className='w-4 h-4 text-purple-500' /> Joint Applicant {index}
        </h4>
        <div className='flex items-center gap-4'>
           <div className='text-xs font-medium text-slate-500'>
             <span className='text-green-600'>{completedDocs.length} Completed</span> | <span className='text-red-500'>{missingDocs.length} Missing</span>
           </div>
           <button onClick={(e) => { e.stopPropagation(); onRemove(index); }} className='text-red-400 hover:text-red-600 bg-red-50 p-1.5 rounded'>
            <X className='w-4 h-4' />
          </button>
        </div>
      </div>
      
      {open && (
        <div className='p-4 space-y-6 bg-white'>
          <form onSubmit={handleSave} className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'>
             <div>
               <label className='block text-xs font-medium text-slate-700 mb-1'>Relationship *</label>
               <select className='input' value={formData.relationship} onChange={(e) => setFormData({...formData, relationship: e.target.value})} required>
                  <option value="">Select Relationship</option>
                  <option value="Father">Father</option>
                  <option value="Mother">Mother</option>
                  <option value="Spouse">Spouse</option>
                  <option value="Brother">Brother</option>
                  <option value="Sister">Sister</option>
                  <option value="Business Partner">Business Partner</option>
                  <option value="Other">Other</option>
               </select>
             </div>
             <div>
               <label className='block text-xs font-medium text-slate-700 mb-1'>Mobile Number *</label>
               <input type="tel" className='input' value={formData.mobile} onChange={(e) => setFormData({...formData, mobile: e.target.value})} required />
             </div>
             <div>
               <label className='block text-xs font-medium text-slate-700 mb-1'>Email (Optional)</label>
               <input type="email" className='input' value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
             </div>
             <div>
               <label className='block text-xs font-medium text-slate-700 mb-1'>Remarks</label>
               <input type="text" className='input' value={formData.remarks} onChange={(e) => setFormData({...formData, remarks: e.target.value})} />
             </div>
             <div className='lg:col-span-4 flex justify-end'>
               <button type="submit" disabled={saving} className='btn-primary text-xs py-1.5 px-4 flex items-center gap-2'>
                 {saving ? <Loader className='w-3 h-3 animate-spin' /> : <CheckCircle className='w-3 h-3' />} Save Details
               </button>
             </div>
          </form>

          <div className='pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4'>
            {JOINT_DOC_TYPES.map((dt) => (
              <DocDropzone key={dt.value} label={dt.label + ' *'} docType={dt.value}
                applicationId={applicationId} jointIndex={index} 
                existingDoc={getDoc(dt.value)} onUploaded={onUploaded} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Applicant Details Form Card ──────────────────────────────────────────────

function ApplicantDetailsCard({ applicationId, uploadedDocs, currentApp, onSaved }) {
  const [form, setForm] = useState({
    applicant_name: '',
    aadhaar_number: '',
    pan_number: '',
    dob: '',
    gender: '',
    address: '',
    father_name: ''
  });
  const [userEdited, setUserEdited] = useState({});
  const [saving, setSaving] = useState(false);
  const [maskAadhaar, setMaskAadhaar] = useState(true);

  // Parse structured_data from documents
  const parseSD = (doc) => {
    if (!doc || !doc.structured_data) return {};
    try { return JSON.parse(doc.structured_data); } catch { return {}; }
  };

  const sortedDocs = [...uploadedDocs].sort((a, b) => (b.id || 0) - (a.id || 0));
  const aadhaarDoc = sortedDocs.find(d => d.document_type === 'aadhaar' && !d.joint_applicant_index);
  const panDoc     = sortedDocs.find(d => d.document_type === 'pan' && !d.joint_applicant_index);

  const aadhaarSD = parseSD(aadhaarDoc);
  const panSD     = parseSD(panDoc);

  const aadhaarProcessing = aadhaarDoc && aadhaarDoc.processed < 2;
  const panProcessing     = panDoc && panDoc.processed < 2;

  // Extracted values by priority
  const extractedName    = aadhaarSD.applicant_name || panSD.applicant_name || null;
  const nameSource       = aadhaarSD.applicant_name ? 'Aadhaar' : (panSD.applicant_name ? 'PAN' : null);

  const extractedAadhaar = aadhaarSD.aadhaar_number || null;

  const extractedPan     = panSD.pan_number || null;

  const extractedDob     = aadhaarSD.dob || panSD.dob || null;
  const dobSource        = aadhaarSD.dob ? 'Aadhaar' : (panSD.dob ? 'PAN' : null);

  const extractedGender  = aadhaarSD.gender || null;

  const extractedAddress = aadhaarSD.address || null;

  const extractedFather  = panSD.father_name || null;

  // Sync saved application values and auto-fill empty fields
  useEffect(() => {
    setForm(prev => {
      const next = { ...prev };
      const app = currentApp || {};

      const resolveVal = (key, extractedVal, savedVal) => {
        if (savedVal) return savedVal;
        if (userEdited[key]) return prev[key];
        if (!prev[key] && extractedVal) return extractedVal;
        return prev[key] || '';
      };

      next.applicant_name = resolveVal('applicant_name', extractedName, app.applicant_name);
      next.aadhaar_number = resolveVal('aadhaar_number', extractedAadhaar, app.aadhaar_number);
      next.pan_number     = resolveVal('pan_number', extractedPan, app.pan_number);
      next.dob            = resolveVal('dob', extractedDob, app.dob);
      next.gender         = resolveVal('gender', extractedGender, app.gender);
      next.address        = resolveVal('address', extractedAddress, app.address);
      next.father_name    = resolveVal('father_name', extractedFather, app.father_name);

      return next;
    });
  }, [currentApp, extractedName, extractedAadhaar, extractedPan, extractedDob, extractedGender, extractedAddress, extractedFather]);

  const normStr = s => (s || '').trim().toLowerCase().replace(/\s+/g, ' ');
  const normAadhaar = s => (s || '').replace(/[\s-]/g, '');
  const normPan = s => (s || '').trim().toUpperCase();
  const normDob = s => (s || '').replace(/[\/\-\.\s]/g, '');

  const areNamesEquivalent = (nameA, nameB) => {
    if (!nameA || !nameB) return true;
    const tokensA = nameA.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(Boolean);
    const tokensB = nameB.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').split(/\s+/).filter(Boolean);
    const setA = new Set(tokensA);
    const setB = new Set(tokensB);
    if (setA.size !== setB.size) return false;
    for (const token of setA) {
      if (!setB.has(token)) return false;
    }
    return true;
  };

  const nameMismatch = (aadhaarSD.applicant_name && panSD.applicant_name) &&
    !areNamesEquivalent(aadhaarSD.applicant_name, panSD.applicant_name);

  const dobMismatch = (aadhaarSD.dob && panSD.dob) &&
    normDob(aadhaarSD.dob) !== normDob(panSD.dob);

  const handleChange = (field, val) => {
    setForm(prev => ({ ...prev, [field]: val }));
    setUserEdited(prev => ({ ...prev, [field]: true }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateApplicantDetails(applicationId, form);
      toast.success('Applicant details saved successfully!');
      if (onSaved) onSaved();
    } catch {
      toast.error('Failed to save applicant details');
    } finally {
      setSaving(false);
    }
  };

  const renderBadge = (fieldName, extractedVal, sourceName, isProcessing) => {
    if (isProcessing) {
      return (
        <span className="text-[11px] font-medium text-amber-600 flex items-center gap-1 mt-1">
          <Loader className="w-3 h-3 animate-spin inline" /> Waiting for document processing...
        </span>
      );
    }
    if (extractedVal) {
      return (
        <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 inline-flex items-center gap-1 mt-1">
          ✓ Extracted from {sourceName}
        </span>
      );
    }
    return (
      <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 inline-flex items-center gap-1 mt-1">
        ⚠ Not extracted — enter manually
      </span>
    );
  };

  const renderMismatchWarning = (fieldName, userVal, extractedVal, normFn, sourceName) => {
    if (!userVal || !extractedVal) return null;
    if (normFn(userVal) === normFn(extractedVal)) return null;

    return (
      <div className="mt-1.5 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1">
        <div className="flex items-center gap-1 text-amber-800 font-semibold">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" /> ⚠ Mismatch detected
        </div>
        <div className="text-slate-600">
          User value: <span className="font-mono font-medium text-slate-800">{userVal}</span>
        </div>
        <div className="text-slate-600">
          Extracted: <span className="font-mono font-medium text-slate-800">{extractedVal}</span>
        </div>
        <div className="flex gap-2 mt-1">
          <button type="button" onClick={() => handleChange(fieldName, extractedVal)}
            className="px-2 py-0.5 bg-amber-600 text-white rounded text-[11px] font-medium hover:bg-amber-700">
            Use Extracted Value
          </button>
          <button type="button" onClick={() => setUserEdited(prev => ({ ...prev, [fieldName]: true }))}
            className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[11px] font-medium hover:bg-slate-300">
            Keep Entered Value
          </button>
        </div>
      </div>
    );
  };

  const formatAadhaarDisplay = (val) => {
    if (!val) return '';
    const clean = normAadhaar(val);
    if (maskAadhaar && clean.length >= 12) {
      return `XXXX XXXX ${clean.slice(-4)}`;
    }
    return val;
  };

  return (
    <Section icon={User} title="Applicant Details" color="blue">
      <form onSubmit={handleSave} className="space-y-4">
        {(nameMismatch || dobMismatch) && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs space-y-1.5 mb-2">
            <div className="flex items-center gap-1.5 text-red-800 font-bold">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" /> ⚠ Aadhaar/PAN information mismatch detected between uploaded documents
            </div>
            {nameMismatch && (
              <div className="text-red-700">
                • <strong>Name:</strong> Aadhaar has <span className="font-semibold">"{aadhaarSD.applicant_name}"</span> vs PAN has <span className="font-semibold">"{panSD.applicant_name}"</span>
              </div>
            )}
            {dobMismatch && (
              <div className="text-red-700">
                • <strong>Date of Birth:</strong> Aadhaar has <span className="font-semibold">"{aadhaarSD.dob}"</span> vs PAN has <span className="font-semibold">"{panSD.dob}"</span>
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Applicant Name */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Applicant Name</label>
            <input type="text" className="input" value={form.applicant_name} onChange={e => handleChange('applicant_name', e.target.value)} placeholder="Full Name" />
            {renderBadge('applicant_name', extractedName, nameSource, aadhaarProcessing || panProcessing)}
            {renderMismatchWarning('applicant_name', form.applicant_name, extractedName, normStr, nameSource)}
          </div>

          {/* Aadhaar Number */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-xs font-medium text-slate-700">Aadhaar Number</label>
              {form.aadhaar_number && (
                <button type="button" onClick={() => setMaskAadhaar(!maskAadhaar)} className="text-[11px] text-blue-600 hover:underline flex items-center gap-1">
                  {maskAadhaar ? 'Unmask' : 'Mask'}
                </button>
              )}
            </div>
            <input type="text" className="input font-mono" value={formatAadhaarDisplay(form.aadhaar_number)} onChange={e => handleChange('aadhaar_number', e.target.value)} placeholder="12-digit Aadhaar Number" />
            {renderBadge('aadhaar_number', extractedAadhaar, 'Aadhaar', aadhaarProcessing)}
            {renderMismatchWarning('aadhaar_number', form.aadhaar_number, extractedAadhaar, normAadhaar, 'Aadhaar')}
          </div>

          {/* PAN Number */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">PAN Number</label>
            <input type="text" className="input font-mono uppercase" value={form.pan_number} onChange={e => handleChange('pan_number', e.target.value.toUpperCase())} placeholder="10-character PAN Number" />
            {renderBadge('pan_number', extractedPan, 'PAN', panProcessing)}
            {renderMismatchWarning('pan_number', form.pan_number, extractedPan, normPan, 'PAN')}
          </div>

          {/* Date of Birth */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Date of Birth</label>
            <input type="text" className="input" value={form.dob} onChange={e => handleChange('dob', e.target.value)} placeholder="DD/MM/YYYY" />
            {renderBadge('dob', extractedDob, dobSource, aadhaarProcessing || panProcessing)}
            {renderMismatchWarning('dob', form.dob, extractedDob, normDob, dobSource)}
          </div>

          {/* Gender */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Gender</label>
            <select className="input" value={form.gender} onChange={e => handleChange('gender', e.target.value)}>
              <option value="">Select Gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Transgender">Transgender</option>
            </select>
            {renderBadge('gender', extractedGender, 'Aadhaar', aadhaarProcessing)}
            {renderMismatchWarning('gender', form.gender, extractedGender, normStr, 'Aadhaar')}
          </div>

          {/* Father's Name */}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Father's Name</label>
            <input type="text" className="input" value={form.father_name} onChange={e => handleChange('father_name', e.target.value)} placeholder="Father's Full Name" />
            {renderBadge('father_name', extractedFather, 'PAN', panProcessing)}
            {renderMismatchWarning('father_name', form.father_name, extractedFather, normStr, 'PAN')}
          </div>

          {/* Address */}
          <div className="sm:col-span-2 lg:col-span-3">
            <label className="block text-xs font-medium text-slate-700 mb-1">Address</label>
            <textarea rows="2" className="input" value={form.address} onChange={e => handleChange('address', e.target.value)} placeholder="Full Postal Address" />
            {renderBadge('address', extractedAddress, 'Aadhaar', aadhaarProcessing)}
            {renderMismatchWarning('address', form.address, extractedAddress, normStr, 'Aadhaar')}
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button type="submit" disabled={saving} className="btn-primary px-6 py-2 flex items-center gap-2">
            {saving ? <Loader className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />} Save Applicant Details
          </button>
        </div>
      </form>
    </Section>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [searchParams] = useSearchParams();
  const [applicationId, setAppId] = useState(searchParams.get('app') || '');
  const [apps, setApps]           = useState([]);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [jointApplicants, setJA]  = useState([1]);

  // Property Details form
  const [propForm, setPropForm] = useState({
    property_type: '', address: '', village_city: '', taluk: '', district: '',
    state: '', pin_code: '', survey_number: '', khata_number: '',
    property_area: '', market_value: '', loan_security_value: ''
  });
  const [savingProp, setSavingProp] = useState(false);

  // Site verification form
  const [siteForm, setSiteForm] = useState({
    officer_name: '', date: '', time: '',
    gps_coordinates: '', remarks: '', property_condition: '',
    construction_quality: '', boundary_present: '', road_access: '',
    utilities_available: []
  });
  const [savingSite, setSavingSite] = useState(false);

  const loadApps = useCallback(() => {
    getApplications().then((r) => setApps(r.data)).catch(() => {});
  }, []);

  useEffect(() => { 
    loadApps(); 
  }, [loadApps]);

  const currentApp = apps.find(a => String(a.id) === String(applicationId));

  const loadDocuments = useCallback(() => {
    if (applicationId) {
      getDocuments(applicationId).then(r => setUploadedDocs(r.data)).catch(() => {});
    } else {
      setUploadedDocs([]);
    }
  }, [applicationId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleSiteSubmit = async (e) => {
    e.preventDefault();
    setSavingSite(true);
    try {
      const payload = {
        ...siteForm,
        utilities_available: siteForm.utilities_available.join(', ')
      };
      await submitSiteVerification(applicationId, payload);
      toast.success('Site verification details saved!');
    } catch { toast.error('Failed to save site verification details'); }
    finally { setSavingSite(false); }
  };

  const handlePropSubmit = async (e) => {
    e.preventDefault();
    setSavingProp(true);
    try {
      await submitPropertyDetails(applicationId, propForm);
      toast.success('Property details saved!');
    } catch { toast.error('Failed to save property details'); }
    finally { setSavingProp(false); }
  };

  const handleGetGPS = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setSiteForm((f) => ({ ...f, gps_coordinates: `${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}` }));
          toast.success('GPS coordinates captured');
        },
        () => toast.error('Could not capture GPS. Enter manually.')
      );
    }
  };

  const addJoint = () => setJA((prev) => [...prev, prev[prev.length - 1] + 1]);
  const removeJoint = (idx) => setJA((prev) => prev.filter((n) => n !== idx));
  const siteUpd = (k, v) => setSiteForm((f) => ({ ...f, [k]: v }));
  
  const toggleUtility = (u) => {
    setSiteForm(f => {
      const ut = f.utilities_available.includes(u) 
        ? f.utilities_available.filter(x => x !== u) 
        : [...f.utilities_available, u];
      return { ...f, utilities_available: ut };
    });
  };

  const propUpd = (k, v) => setPropForm(f => ({ ...f, [k]: v }));
  
  const getDoc = (dt, jointIndex = null) => {
    return [...uploadedDocs].reverse().find(d => d.document_type === dt && d.joint_applicant_index === jointIndex);
  };

  return (
    <div className='max-w-6xl mx-auto space-y-6 pb-12'>
      {/* Application selector */}
      <div className='card shadow-sm rounded-xl'>
        <h2 className='font-semibold text-slate-700 mb-3 text-lg'>Select Application</h2>
        <select value={applicationId} onChange={(e) => setAppId(e.target.value)} className='input max-w-xl text-base py-2.5'>
          <option value=''>— Choose an application —</option>
          {apps.map((a) => (
            <option key={a.id} value={a.id}>
              #{a.id} — {a.branch || 'Unknown Branch'} | {a.loan_type || '—'} | ₹{Number(a.loan_amount).toLocaleString('en-IN')}
            </option>
          ))}
        </select>
      </div>

      {!applicationId && (
        <div className='card text-center py-20 text-slate-400 shadow-sm rounded-xl bg-slate-50/50'>
          <Upload className='w-12 h-12 mx-auto mb-4 text-slate-300' />
          <p className='text-lg'>Please select an application above to begin uploading documents.</p>
        </div>
      )}

      {applicationId && (
        <div className='space-y-6'>
          
          {/* Document Validation Dashboard */}
          <div className='card shadow-sm rounded-xl bg-white border border-blue-100'>
            <div className='flex items-center gap-3 border-b pb-4 mb-4'>
              <FileCheck className='w-6 h-6 text-blue-600' />
              <h3 className='font-semibold text-lg text-slate-800'>Document Validation</h3>
            </div>
            <div className='grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3'>
              {APPLICANT_DOCS.map(doc => {
                const isUploaded = !!getDoc(doc.value);
                return (
                  <div key={doc.value} className='flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 transition-colors'>
                    <div className='flex items-center gap-2 text-sm'>
                      {isUploaded ? <CheckCircle className='w-5 h-5 text-green-500' /> : <AlertCircle className='w-5 h-5 text-amber-500' />}
                      <span className={`font-medium ${isUploaded ? 'text-slate-700' : 'text-slate-600'}`}>
                        {doc.label} {doc.required && <span className='text-red-500'>*</span>}
                      </span>
                    </div>
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${isUploaded ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {isUploaded ? 'Uploaded' : 'Pending'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Applicant Details Form */}
          <ApplicantDetailsCard applicationId={applicationId} uploadedDocs={uploadedDocs} currentApp={currentApp} onSaved={loadApps} />

          {/* Applicant Documents */}
          <Section icon={User} title='Applicant Documents' color='blue'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-5'>
              {APPLICANT_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label + (dt.required ? ' *' : '')} docType={dt.value}
                  applicationId={applicationId} existingDoc={getDoc(dt.value)} onUploaded={loadDocuments} />
              ))}
            </div>
          </Section>

          {/* Employment Documents */}
          <Section icon={Briefcase} title='Employment Documents' color='green'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-5'>
              {EMPLOYMENT_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} existingDoc={getDoc(dt.value)} onUploaded={loadDocuments} />
              ))}
            </div>
          </Section>

          {/* Joint Applicants */}
          <Section icon={User} title='Joint Applicants' color='purple'>
            <div className='space-y-5'>
              {(() => {
                let uploaded = 0;
                let total = jointApplicants.length * JOINT_DOC_TYPES.length;
                jointApplicants.forEach(idx => {
                  JOINT_DOC_TYPES.forEach(dt => {
                    if (getDoc(dt.value, idx)) uploaded++;
                  });
                });
                return (
                  <div className='flex gap-6 p-4 bg-purple-50 rounded-xl border border-purple-100 text-sm font-medium text-purple-900'>
                    <div>Total Applicants: {jointApplicants.length}</div>
                    <div>Documents Uploaded: {uploaded}</div>
                    <div className='text-red-600'>Pending Documents: {total - uploaded}</div>
                  </div>
                );
              })()}

              {jointApplicants.map((idx) => (
                <JointApplicantCard key={idx} index={idx}
                  applicationId={applicationId} onRemove={removeJoint} 
                  uploadedDocs={uploadedDocs} onUploaded={loadDocuments} />
              ))}
              <button onClick={addJoint} className='btn-secondary flex items-center gap-2 text-sm w-full justify-center py-3 border-dashed hover:border-purple-300 hover:text-purple-700'>
                <Plus className='w-4 h-4' /> Add Joint Applicant
              </button>
            </div>
          </Section>

          {/* Property Summary Dashboard */}
          {(() => {
            const reqDocs = PROPERTY_DOCS.filter(d => d.required);
            const docsUp = PROPERTY_DOCS.filter(d => getDoc(d.value)).length;
            const imgsUp = PROPERTY_IMAGES.filter(d => getDoc(d.value)).length;
            const pendingDocs = reqDocs.filter(d => !getDoc(d.value)).length + (imgsUp === 0 ? 1 : 0);
            return (
              <div className='card shadow-sm rounded-xl bg-white border border-orange-100'>
                <div className='flex items-center gap-3 border-b pb-4 mb-4'>
                  <Home className='w-6 h-6 text-orange-600' />
                  <h3 className='font-semibold text-lg text-slate-800'>Property Summary</h3>
                </div>
                <div className='grid grid-cols-2 sm:grid-cols-5 gap-4 text-sm'>
                  <div className='bg-orange-50 p-3 rounded-lg'>
                    <div className='text-xs text-orange-600 mb-1'>Property Type</div>
                    <div className='font-semibold'>{propForm.property_type || '—'}</div>
                  </div>
                  <div className='bg-orange-50 p-3 rounded-lg'>
                    <div className='text-xs text-orange-600 mb-1'>Market Value</div>
                    <div className='font-semibold'>{propForm.market_value ? `₹${propForm.market_value}` : '—'}</div>
                  </div>
                  <div className='bg-green-50 p-3 rounded-lg'>
                    <div className='text-xs text-green-600 mb-1'>Docs Uploaded</div>
                    <div className='font-semibold'>{docsUp}</div>
                  </div>
                  <div className='bg-teal-50 p-3 rounded-lg'>
                    <div className='text-xs text-teal-600 mb-1'>Images Uploaded</div>
                    <div className='font-semibold'>{imgsUp}</div>
                  </div>
                  <div className='bg-red-50 p-3 rounded-lg'>
                    <div className='text-xs text-red-600 mb-1'>Pending Required</div>
                    <div className='font-semibold text-red-600'>{pendingDocs}</div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Property Details Form */}
          <Section icon={Home} title='Property Details' color='orange'>
            <form onSubmit={handlePropSubmit} className='space-y-4'>
              <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Property Type</label>
                  <select className='input' value={propForm.property_type} onChange={e => propUpd('property_type', e.target.value)} required>
                    <option value="">Select</option>
                    <option value="Residential House">Residential House</option>
                    <option value="Apartment">Apartment</option>
                    <option value="Commercial Building">Commercial Building</option>
                    <option value="Agricultural Land">Agricultural Land</option>
                    <option value="Open Site">Open Site</option>
                    <option value="Industrial Property">Industrial Property</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Market Value (₹)</label>
                  <input type='number' className='input' value={propForm.market_value} onChange={e => propUpd('market_value', e.target.value)} />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Loan Security Value (₹)</label>
                  <input type='number' className='input' value={propForm.loan_security_value} onChange={e => propUpd('loan_security_value', e.target.value)} />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Property Area</label>
                  <input type='text' className='input' value={propForm.property_area} onChange={e => propUpd('property_area', e.target.value)} required placeholder='e.g. 1200 sq.ft' />
                </div>
                <div className='lg:col-span-4'>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Property Address</label>
                  <input type='text' className='input' value={propForm.address} onChange={e => propUpd('address', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Village / City</label>
                  <input type='text' className='input' value={propForm.village_city} onChange={e => propUpd('village_city', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Taluk</label>
                  <input type='text' className='input' value={propForm.taluk} onChange={e => propUpd('taluk', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>District</label>
                  <input type='text' className='input' value={propForm.district} onChange={e => propUpd('district', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>State</label>
                  <input type='text' className='input' value={propForm.state} onChange={e => propUpd('state', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>PIN Code</label>
                  <input type='text' className='input' value={propForm.pin_code} onChange={e => propUpd('pin_code', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Survey Number</label>
                  <input type='text' className='input' value={propForm.survey_number} onChange={e => propUpd('survey_number', e.target.value)} required />
                </div>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Khata Number (Optional)</label>
                  <input type='text' className='input' value={propForm.khata_number} onChange={e => propUpd('khata_number', e.target.value)} />
                </div>
              </div>
              <div className='flex justify-end pt-2'>
                <button type='submit' disabled={savingProp} className='btn-primary px-6 py-2 flex items-center gap-2'>
                  {savingProp ? <Loader className='w-4 h-4 animate-spin' /> : <CheckCircle className='w-4 h-4' />} Save Property Details
                </button>
              </div>
            </form>
          </Section>

          {/* Property Documents */}
          <Section icon={Home} title='Property Documents' color='orange'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-5'>
              {PROPERTY_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label + (dt.required ? ' *' : '')} docType={dt.value}
                  applicationId={applicationId} existingDoc={getDoc(dt.value)} onUploaded={loadDocuments} />
              ))}
            </div>
          </Section>

          {/* Property Images */}
          <Section icon={Image} title='Property Images' color='teal'>
            <div className='grid grid-cols-2 sm:grid-cols-5 gap-4'>
              {PROPERTY_IMAGES.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} existingDoc={getDoc(dt.value)} onUploaded={loadDocuments} />
              ))}
            </div>
          </Section>

          {/* Site Verification Summary Dashboard */}
          {(() => {
            const imgsUp = PROPERTY_IMAGES.filter(d => getDoc(`geo_${d.value}`)).length;
            const totalImgs = PROPERTY_IMAGES.length;
            const pendingImgs = totalImgs - imgsUp;
            return (
              <div className='card shadow-sm rounded-xl bg-white border border-indigo-100 mt-6'>
                <div className='flex items-center gap-3 border-b pb-4 mb-4'>
                  <MapPin className='w-6 h-6 text-indigo-600' />
                  <h3 className='font-semibold text-lg text-slate-800'>Site Visit Summary</h3>
                </div>
                <div className='grid grid-cols-2 sm:grid-cols-6 gap-4 text-sm'>
                  <div className='bg-indigo-50 p-3 rounded-lg'>
                    <div className='text-xs text-indigo-600 mb-1'>Officer Name</div>
                    <div className='font-semibold truncate' title={siteForm.officer_name || '—'}>{siteForm.officer_name || '—'}</div>
                  </div>
                  <div className='bg-indigo-50 p-3 rounded-lg'>
                    <div className='text-xs text-indigo-600 mb-1'>Visit Date</div>
                    <div className='font-semibold'>{siteForm.date || '—'}</div>
                  </div>
                  <div className='bg-blue-50 p-3 rounded-lg'>
                    <div className='text-xs text-blue-600 mb-1'>GPS Status</div>
                    <div className={`font-semibold ${siteForm.gps_coordinates ? 'text-green-600' : 'text-slate-500'}`}>
                      {siteForm.gps_coordinates ? 'Captured' : 'Pending'}
                    </div>
                  </div>
                  <div className='bg-teal-50 p-3 rounded-lg'>
                    <div className='text-xs text-teal-600 mb-1'>Images Uploaded</div>
                    <div className='font-semibold'>{imgsUp} / {totalImgs}</div>
                  </div>
                  <div className='bg-orange-50 p-3 rounded-lg'>
                    <div className='text-xs text-orange-600 mb-1'>Property Condition</div>
                    <div className='font-semibold'>{siteForm.property_condition || '—'}</div>
                  </div>
                  <div className='bg-red-50 p-3 rounded-lg'>
                    <div className='text-xs text-red-600 mb-1'>Pending Items</div>
                    <div className='font-semibold text-red-600'>{pendingImgs + (!siteForm.gps_coordinates ? 1 : 0) + (!siteForm.officer_name ? 1 : 0)}</div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Site Verification */}
          <Section icon={MapPin} title='Site Verification Details' color='indigo'>
            <form onSubmit={handleSiteSubmit} className='space-y-6'>
              
              <div className='bg-slate-50 p-4 rounded-lg border border-slate-200'>
                <h4 className='font-semibold text-slate-700 mb-4 text-sm flex items-center gap-2'>
                  <User className='w-4 h-4 text-indigo-500' /> Field Officer Details
                </h4>
                <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Officer Name *</label>
                    <input type='text' value={siteForm.officer_name} onChange={(e) => siteUpd('officer_name', e.target.value)} className='input' placeholder='Full name' required />
                  </div>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Visit Date *</label>
                    <input type='date' value={siteForm.date} onChange={(e) => siteUpd('date', e.target.value)} className='input' required />
                  </div>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Visit Time *</label>
                    <input type='time' value={siteForm.time} onChange={(e) => siteUpd('time', e.target.value)} className='input' required />
                  </div>
                </div>
              </div>

              <div className='bg-slate-50 p-4 rounded-lg border border-slate-200'>
                <h4 className='font-semibold text-slate-700 mb-4 text-sm flex items-center gap-2'>
                  <MapPin className='w-4 h-4 text-blue-500' /> GPS Location
                </h4>
                <div>
                  <label className='block text-xs font-medium text-slate-700 mb-1'>Coordinates</label>
                  <div className='flex gap-2 max-w-md'>
                    <input type='text' value={siteForm.gps_coordinates} onChange={(e) => siteUpd('gps_coordinates', e.target.value)} className='input' placeholder='Lat, Long' />
                    <button type='button' onClick={handleGetGPS} className='btn-secondary px-4 flex-shrink-0 flex items-center gap-2' title='Capture GPS'>
                      <MapPin className='w-4 h-4' /> Capture
                    </button>
                  </div>
                  {siteForm.gps_coordinates && (
                     <p className='text-xs mt-2 text-green-600 font-medium flex items-center gap-1'>
                       <CheckCircle className='w-3 h-3' /> GPS Captured
                     </p>
                  )}
                </div>
              </div>

              <div className='bg-slate-50 p-4 rounded-lg border border-slate-200'>
                <h4 className='font-semibold text-slate-700 mb-4 text-sm flex items-center gap-2'>
                  <FileCheck className='w-4 h-4 text-orange-500' /> Property Observations
                </h4>
                <div className='grid grid-cols-1 sm:grid-cols-2 gap-5'>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Property Condition</label>
                    <select value={siteForm.property_condition} onChange={(e) => siteUpd('property_condition', e.target.value)} className='input'>
                      <option value=''>Select Condition</option>
                      {['Excellent', 'Good', 'Average', 'Poor', 'Under Construction', 'Occupied', 'Vacant'].map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Construction Quality</label>
                    <select value={siteForm.construction_quality} onChange={(e) => siteUpd('construction_quality', e.target.value)} className='input'>
                      <option value=''>Select Quality</option>
                      {['Premium', 'Standard', 'Basic', 'Poor'].map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Boundary Present</label>
                    <select value={siteForm.boundary_present} onChange={(e) => siteUpd('boundary_present', e.target.value)} className='input'>
                      <option value=''>Select</option>
                      <option value='Yes'>Yes</option>
                      <option value='No'>No</option>
                    </select>
                  </div>
                  <div>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Road Access</label>
                    <select value={siteForm.road_access} onChange={(e) => siteUpd('road_access', e.target.value)} className='input'>
                      <option value=''>Select</option>
                      <option value='Yes'>Yes</option>
                      <option value='No'>No</option>
                    </select>
                  </div>
                  <div className='sm:col-span-2'>
                    <label className='block text-xs font-medium text-slate-700 mb-2'>Utilities Available</label>
                    <div className='flex flex-wrap gap-4'>
                      {['Electricity', 'Water', 'Drainage', 'Internet'].map(u => (
                        <label key={u} className='flex items-center gap-2 text-sm text-slate-700 cursor-pointer'>
                          <input type='checkbox' checked={siteForm.utilities_available.includes(u)} onChange={() => toggleUtility(u)} className='rounded border-slate-300 text-blue-600 focus:ring-blue-500' />
                          {u}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className='sm:col-span-2'>
                    <label className='block text-xs font-medium text-slate-700 mb-1'>Officer Remarks</label>
                    <textarea value={siteForm.remarks} onChange={(e) => siteUpd('remarks', e.target.value)} className='input' rows='3' placeholder='Enter detailed observations, findings…' />
                  </div>
                </div>
              </div>

              {/* Geo-tagged images */}
              <div className='bg-slate-50 p-4 rounded-lg border border-slate-200'>
                <h4 className='font-semibold text-slate-700 mb-4 text-sm flex items-center gap-2'>
                  <Image className='w-4 h-4 text-teal-500' /> Site Images
                </h4>
                <div className='grid grid-cols-2 sm:grid-cols-5 gap-4'>
                  {PROPERTY_IMAGES.map((img) => (
                    <DocDropzone key={`geo_${img.value}`} label={img.label}
                      docType={`geo_${img.value}`} applicationId={applicationId} 
                      existingDoc={getDoc(`geo_${img.value}`)} onUploaded={loadDocuments} />
                  ))}
                </div>
              </div>

              <div className='flex justify-end pt-2'>
                <button type='submit' disabled={savingSite} className='btn-primary px-8 py-2.5 flex items-center gap-2'>
                  {savingSite ? <Loader className='w-4 h-4 animate-spin' /> : <CheckCircle className='w-4 h-4' />} Save Site Verification
                </button>
              </div>
            </form>
          </Section>
        </div>
      )}
    </div>
  );
}
