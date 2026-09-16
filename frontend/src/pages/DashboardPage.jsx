import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { FileText, Clock, MapPin, TrendingUp } from 'lucide-react';
import { getDashboardStats } from '../services/api';
import StatCard from '../components/ui/StatCard';
import BranchSelect from '../components/ui/BranchSelect';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [branch, setBranch]   = useState('');

  const fetchStats = (b) => {
    const effectiveBranch = (b === '__other__') ? '' : b;
    setLoading(true);
    getDashboardStats(effectiveBranch)
      .then((r) => setStats(r.data))
      .catch(() => toast.error('Failed to load dashboard stats'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchStats(branch); }, [branch]);

  return (
    <div className='space-y-6'>
      {/* Branch filter */}
      <div className='card p-4 flex flex-wrap items-center gap-4'>
        <span className='text-sm font-semibold text-slate-700 whitespace-nowrap'>Filter by Branch:</span>
        <div className='w-72'>
          <BranchSelect value={branch} onChange={setBranch} />
        </div>
        {branch && branch !== '__other__' && (
          <button onClick={() => setBranch('')} className='text-xs text-slate-500 underline'>Clear</button>
        )}
      </div>

      {loading ? <LoadingSpinner size='lg' /> : stats && (
        <>
          {/* Stat cards – exactly 4 */}
          <div className='grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4'>
            <StatCard label='Pending Applications'      value={stats.pending_applications}            icon={FileText}    color='blue'   />
            <StatCard label='Under Verification'        value={stats.applications_under_verification} icon={Clock}       color='yellow' />
            <StatCard label='Pending Site Visits'       value={stats.pending_site_visits}             icon={MapPin}      color='red'    />
            <StatCard label='Avg Processing Time'       value={stats.average_processing_time}         icon={TrendingUp}  color='green'  />
          </div>

          {/* Monthly trend chart */}
          {stats.monthly_trend && stats.monthly_trend.length > 0 && (
            <div className='card'>
              <h3 className='text-base font-semibold text-slate-700 mb-4'>Monthly Application Trend</h3>
              <ResponsiveContainer width='100%' height={260}>
                <BarChart data={stats.monthly_trend}>
                  <CartesianGrid strokeDasharray='3 3' stroke='#f1f5f9' />
                  <XAxis dataKey='month' tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey='count' fill='#3b82f6' radius={[4,4,0,0]} name='Applications' />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
