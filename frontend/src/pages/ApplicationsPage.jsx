import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Upload, RefreshCw, Play, ShieldCheck, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { getApplications, createApplication, deleteApplication } from '../services/api';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import BranchSelect from '../components/ui/BranchSelect';
import { formatCurrency, formatDate } from '../utils/formatters';
import { LOAN_TYPES } from '../utils/constants';

const EMPTY_FORM = { branch: '', loan_type: '', loan_amount: '', loan_tenure: '', interest_rate: '' };

export default function ApplicationsPage() {
  const [apps, setApps]           = useState([]);
  const [loading, setLoading]     = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm]           = useState(EMPTY_FORM);
  const [saving, setSaving]       = useState(false);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    getApplications()
      .then((r) => setApps(r.data))
      .catch(() => toast.error('Failed to load applications'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleCreate = async (e) => {
    e.preventDefault();
    const branch = form.branch === '__other__' ? '' : form.branch;
    if (!branch) { toast.error('Please enter a branch name'); return; }
    setSaving(true);
    try {
      await createApplication({
        branch,
        loan_type:     form.loan_type,
        loan_amount:   parseFloat(form.loan_amount),
        loan_tenure:   parseInt(form.loan_tenure, 10),
        interest_rate: form.interest_rate ? parseFloat(form.interest_rate) : null,
      });
      toast.success('Application created!');
      setShowModal(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Creation failed');
    } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this application?')) return;
    try {
      await deleteApplication(id);
      toast.success('Deleted');
      setApps((prev) => prev.filter((a) => a.id !== id));
    } catch { toast.error('Delete failed'); }
  };

  return (
    <div className='space-y-6'>
      {/* Top bar */}
      <div className='flex items-center justify-between'>
        <p className='text-sm text-slate-500'>{apps.length} application(s)</p>
        <div className='flex gap-2'>
          <button onClick={load} className='btn-secondary flex items-center gap-2'>
            <RefreshCw className='w-4 h-4' /> Refresh
          </button>
          <button onClick={() => setShowModal(true)} className='btn-primary flex items-center gap-2'>
            <Plus className='w-4 h-4' /> New Application
          </button>
        </div>
      </div>

      {/* Table */}
      {loading ? <LoadingSpinner /> : (
        <div className='card p-0 overflow-x-auto'>
          <table className='w-full text-sm min-w-[800px]'>
            <thead className='bg-slate-50 border-b border-slate-200'>
              <tr>
                {['ID','Branch','Loan Type','Loan Amount','Status','Officer','Created','Actions'].map((h) => (
                  <th key={h} className='text-left px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wide'>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {apps.length === 0 ? (
                <tr><td colSpan={8} className='text-center py-16 text-slate-400'>No applications yet. Click New Application to start.</td></tr>
              ) : apps.map((app) => (
                <tr key={app.id} className='border-b border-slate-100 hover:bg-slate-50 transition-colors'>
                  <td className='px-4 py-3 font-mono text-slate-400 text-xs'>#{app.id}</td>
                  <td className='px-4 py-3 font-medium text-slate-800'>{app.branch || '—'}</td>
                  <td className='px-4 py-3 text-slate-600'>{app.loan_type || '—'}</td>
                  <td className='px-4 py-3 font-semibold'>{formatCurrency(app.loan_amount)}</td>
                  <td className='px-4 py-3'><StatusBadge status={app.status} /></td>
                  <td className='px-4 py-3 text-slate-500'>{app.officer_name || '—'}</td>
                  <td className='px-4 py-3 text-slate-500'>{formatDate(app.created_at)}</td>
                  <td className='px-4 py-3'>
                    <div className='flex gap-1'>
                      <button onClick={() => navigate(`/upload?app=${app.id}`)}
                        className='p-1.5 rounded-lg text-blue-600 hover:bg-blue-50' title='Upload Documents'>
                        <Upload className='w-4 h-4' />
                      </button>
                      <button onClick={() => navigate(`/verify?app=${app.id}`)}
                        className='p-1.5 rounded-lg text-green-600 hover:bg-green-50' title='Run Verification'>
                        <Play className='w-4 h-4' />
                      </button>
                      <button onClick={() => navigate(`/gov-verify/${app.id}`)}
                        className='p-1.5 rounded-lg text-amber-600 hover:bg-amber-50' title='Gov Verification'>
                        <ShieldCheck className='w-4 h-4' />
                      </button>
                      <button onClick={() => navigate(`/report/${app.id}`)}
                        className='p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50' title='View Report'>
                        <FileText className='w-4 h-4' />
                      </button>
                      <button onClick={() => handleDelete(app.id)}
                        className='p-1.5 rounded-lg text-red-500 hover:bg-red-50' title='Delete'>
                        <Trash2 className='w-4 h-4' />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className='fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4'>
          <div className='bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto'>
            <h2 className='text-lg font-bold mb-5 text-slate-800'>New Loan Application</h2>
            <form onSubmit={handleCreate} className='space-y-4'>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Branch <span className='text-red-500'>*</span></label>
                <BranchSelect value={form.branch} onChange={(v) => upd('branch', v)} required />
              </div>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Loan Type <span className='text-red-500'>*</span></label>
                <select required value={form.loan_type} onChange={(e) => upd('loan_type', e.target.value)} className='input'>
                  <option value=''>Select Loan Type</option>
                  {LOAN_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Loan Amount (INR) <span className='text-red-500'>*</span></label>
                <input type='number' required min='10000' value={form.loan_amount}
                  onChange={(e) => upd('loan_amount', e.target.value)}
                  placeholder='e.g. 5000000' className='input' />
              </div>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Loan Tenure (Months) <span className='text-red-500'>*</span></label>
                <input type='number' required min='1' max='360' value={form.loan_tenure}
                  onChange={(e) => upd('loan_tenure', e.target.value)}
                  placeholder='e.g. 240' className='input' />
              </div>
              <div>
                <label className='block text-sm font-medium text-slate-700 mb-1'>Interest Rate (% p.a.) <span className='text-slate-400 text-xs'>Optional</span></label>
                <input type='number' step='0.01' min='0' max='50' value={form.interest_rate}
                  onChange={(e) => upd('interest_rate', e.target.value)}
                  placeholder='e.g. 8.5' className='input' />
              </div>
              <div className='flex gap-3 pt-2'>
                <button type='button' onClick={() => { setShowModal(false); setForm(EMPTY_FORM); }} className='btn-secondary flex-1'>
                  Cancel
                </button>
                <button type='submit' disabled={saving} className='btn-primary flex-1'>
                  {saving ? 'Creating…' : 'Create Application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
