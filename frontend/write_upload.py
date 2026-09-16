
# write_upload.py
import os, textwrap

content = '''
import React, { useState, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileCheck, AlertCircle, Loader, Plus, X,
  MapPin, Camera, ChevronDown, ChevronUp, User, Briefcase, Home, Image
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  uploadDocument, processDocument, getDocuments,
  getApplications, submitSiteVerification
} from '../services/api';
import { PROPERTY_CONDITIONS } from '../utils/constants';

// ─── Document sections config ─────────────────────────────────────────────────

const APPLICANT_DOCS = [
  { value: 'aadhaar',         label: 'Aadhaar Card' },
  { value: 'pan',             label: 'PAN Card' },
  { value: 'passport_photo',  label: 'Passport Photograph' },
];

const EMPLOYMENT_DOCS = [
  { value: 'salary_slip',     label: 'Salary Slip' },
  { value: 'employment_cert', label: 'Employment Certificate' },
  { value: 'form_16',         label: 'Form 16' },
];

const PROPERTY_DOCS = [
  { value: 'sale_deed',          label: 'Sale Deed' },
  { value: 'tax_receipt',        label: 'Tax Receipt' },
  { value: 'encumbrance_cert',   label: 'Encumbrance Certificate' },
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
  { value: 'employment_cert', label: 'Employment Certificate' },
];

// ─── Dropzone helper ──────────────────────────────────────────────────────────

function DocDropzone({ label, docType, applicationId, jointIndex, onUploaded }) {
  const [file, setFile]         = useState(null);
  const [uploading, setUploading] = useState(false);
  const [done, setDone]         = useState(false);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setFile(accepted[0]);
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
    try {
      const fd = new FormData();
      fd.append('application_id', applicationId);
      fd.append('document_type', docType);
      if (jointIndex !== undefined) fd.append('joint_applicant_index', jointIndex);
      fd.append('file', file);
      const { data: doc } = await uploadDocument(fd);
      await processDocument(doc.id);
      setDone(true);
      setFile(null);
      toast.success(`${label} uploaded and processed!`);
      if (onUploaded) onUploaded();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to upload ${label}`);
    } finally { setUploading(false); }
  };

  if (done) {
    return (
      <div className='flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg'>
        <FileCheck className='w-5 h-5 text-green-500 flex-shrink-0' />
        <span className='text-sm font-medium text-green-700'>{label}</span>
        <button onClick={() => setDone(false)} className='ml-auto text-xs text-green-600 underline'>Re-upload</button>
      </div>
    );
  }

  return (
    <div className='space-y-2'>
      <p className='text-sm font-medium text-slate-700'>{label}</p>
      <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-300 hover:border-blue-400'}`}>
        <input {...getInputProps()} />
        {file ? (
          <p className='text-sm text-blue-700 font-medium truncate'>{file.name}</p>
        ) : (
          <p className='text-xs text-slate-500'>{isDragActive ? 'Drop here' : 'Drag & drop or click to browse'}</p>
        )}
      </div>
      {file && (
        <div className='flex gap-2'>
          <button onClick={handleUpload} disabled={uploading}
            className='btn-primary flex-1 flex items-center justify-center gap-1 text-xs py-1.5'>
            {uploading ? <Loader className='w-3 h-3 animate-spin' /> : <Upload className='w-3 h-3' />}
            {uploading ? 'Processing…' : 'Upload & Process'}
          </button>
          <button onClick={() => setFile(null)} className='p-1.5 text-slate-400 hover:text-slate-600'>
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
    <div className='card overflow-hidden p-0'>
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

function JointApplicantCard({ index, applicationId, onRemove }) {
  return (
    <div className='border border-slate-200 rounded-xl p-4 space-y-3'>
      <div className='flex items-center justify-between'>
        <h4 className='font-semibold text-slate-700 text-sm flex items-center gap-2'>
          <User className='w-4 h-4 text-purple-500' /> Joint Applicant {index}
        </h4>
        <button onClick={() => onRemove(index)} className='text-red-400 hover:text-red-600'>
          <X className='w-4 h-4' />
        </button>
      </div>
      <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
        {JOINT_DOC_TYPES.map((dt) => (
          <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
            applicationId={applicationId} jointIndex={index} />
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [searchParams] = useSearchParams();
  const [applicationId, setAppId] = useState(searchParams.get('app') || '');
  const [apps, setApps]           = useState([]);
  const [jointApplicants, setJA]  = useState([1]);
  const [refresh, setRefresh]     = useState(0);

  // Site verification form
  const [siteForm, setSiteForm] = useState({
    officer_name: '', officer_id: '', date: '', time: '',
    gps_coordinates: '', remarks: '', property_condition: '',
  });
  const [savingSite, setSavingSite] = useState(false);

  useEffect(() => { getApplications().then((r) => setApps(r.data)).catch(() => {}); }, []);

  const handleSiteSubmit = async (e) => {
    e.preventDefault();
    setSavingSite(true);
    try {
      await submitSiteVerification(applicationId, siteForm);
      toast.success('Site verification details saved!');
    } catch { toast.error('Failed to save site verification details'); }
    finally { setSavingSite(false); }
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

  return (
    <div className='max-w-5xl mx-auto space-y-5'>
      {/* Application selector */}
      <div className='card'>
        <h2 className='font-semibold text-slate-700 mb-3'>Select Application</h2>
        <select value={applicationId} onChange={(e) => setAppId(e.target.value)} className='input max-w-md'>
          <option value=''>— Choose an application —</option>
          {apps.map((a) => (
            <option key={a.id} value={a.id}>
              #{a.id} — {a.branch || 'Unknown Branch'} | {a.loan_type || '—'} | ₹{Number(a.loan_amount).toLocaleString('en-IN')}
            </option>
          ))}
        </select>
      </div>

      {!applicationId && (
        <div className='card text-center py-16 text-slate-400'>
          <Upload className='w-10 h-10 mx-auto mb-3 opacity-40' />
          <p>Please select an application above to upload documents.</p>
        </div>
      )}

      {applicationId && (
        <div className='space-y-5'>
          {/* Applicant Documents */}
          <Section icon={User} title='Applicant Documents' color='blue'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-4'>
              {APPLICANT_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} onUploaded={() => setRefresh((r) => r + 1)} />
              ))}
            </div>
          </Section>

          {/* Employment Documents */}
          <Section icon={Briefcase} title='Employment Documents' color='green'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-4'>
              {EMPLOYMENT_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} onUploaded={() => setRefresh((r) => r + 1)} />
              ))}
            </div>
          </Section>

          {/* Joint Applicants */}
          <Section icon={User} title='Joint Applicants' color='purple'>
            <div className='space-y-4'>
              {jointApplicants.map((idx) => (
                <JointApplicantCard key={idx} index={idx}
                  applicationId={applicationId} onRemove={removeJoint} />
              ))}
              <button onClick={addJoint} className='btn-secondary flex items-center gap-2 text-sm'>
                <Plus className='w-4 h-4' /> Add Joint Applicant
              </button>
            </div>
          </Section>

          {/* Property Documents */}
          <Section icon={Home} title='Property Documents' color='orange'>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-4'>
              {PROPERTY_DOCS.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} onUploaded={() => setRefresh((r) => r + 1)} />
              ))}
            </div>
          </Section>

          {/* Property Images */}
          <Section icon={Image} title='Property Images' color='teal'>
            <div className='grid grid-cols-2 sm:grid-cols-5 gap-3'>
              {PROPERTY_IMAGES.map((dt) => (
                <DocDropzone key={dt.value} label={dt.label} docType={dt.value}
                  applicationId={applicationId} onUploaded={() => setRefresh((r) => r + 1)} />
              ))}
            </div>
          </Section>

          {/* Site Verification */}
          <Section icon={MapPin} title='Site Verification' color='indigo'>
            <form onSubmit={handleSiteSubmit} className='space-y-4'>
              <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>Officer Name</label>
                  <input type='text' value={siteForm.officer_name}
                    onChange={(e) => siteUpd('officer_name', e.target.value)}
                    className='input' placeholder='Full name' />
                </div>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>Officer ID</label>
                  <input type='text' value={siteForm.officer_id}
                    onChange={(e) => siteUpd('officer_id', e.target.value)}
                    className='input' placeholder='Employee ID' />
                </div>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>Visit Date</label>
                  <input type='date' value={siteForm.date}
                    onChange={(e) => siteUpd('date', e.target.value)} className='input' />
                </div>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>Visit Time</label>
                  <input type='time' value={siteForm.time}
                    onChange={(e) => siteUpd('time', e.target.value)} className='input' />
                </div>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>Property Condition</label>
                  <select value={siteForm.property_condition}
                    onChange={(e) => siteUpd('property_condition', e.target.value)} className='input'>
                    <option value=''>Select Condition</option>
                    {PROPERTY_CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className='block text-sm font-medium text-slate-700 mb-1'>GPS Coordinates</label>
                  <div className='flex gap-2'>
                    <input type='text' value={siteForm.gps_coordinates}
                      onChange={(e) => siteUpd('gps_coordinates', e.target.value)}
                      className='input' placeholder='Lat, Long' />
                    <button type='button' onClick={handleGetGPS}
                      className='btn-secondary px-2 flex-shrink-0' title='Capture GPS'>
                      <MapPin className='w-4 h-4' />
                    </button>
                  </div>
                </div>
              </div>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Officer Remarks</label>
                <textarea value={siteForm.remarks}
                  onChange={(e) => siteUpd('remarks', e.target.value)}
                  className='input' rows='3' placeholder='Enter observations, findings…' />
              </div>

              {/* Geo-tagged images */}
              <div>
                <p className='text-sm font-medium text-slate-700 mb-3'>Geo-tagged Site Photos</p>
                <div className='grid grid-cols-2 sm:grid-cols-5 gap-3'>
                  {PROPERTY_IMAGES.map((img) => (
                    <DocDropzone key={`geo_${img.value}`} label={img.label}
                      docType={`geo_${img.value}`} applicationId={applicationId} />
                  ))}
                </div>
              </div>

              <button type='submit' disabled={savingSite}
                className='btn-primary flex items-center gap-2'>
                {savingSite ? <Loader className='w-4 h-4 animate-spin' /> : <Camera className='w-4 h-4' />}
                {savingSite ? 'Saving…' : 'Save Site Verification'}
              </button>
            </form>
          </Section>
        </div>
      )}
    </div>
  );
}
'''

os.makedirs('src/pages', exist_ok=True)
with open('src/pages/UploadPage.jsx', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content.lstrip('\n'))
print('UploadPage.jsx written')
