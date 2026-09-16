
import os

content = '''
import React from 'react';
import { CheckCircle, AlertTriangle, XCircle, Clock, Search, ExternalLink } from 'lucide-react';

const GovVerification = () => {
  // Hardcoded UI placeholders as requested
  const verifications = [
    { name: 'Aadhaar Verification', status: 'verified', timestamp: '2023-11-20 10:45 AM', officer: 'Auto-System', doc: 'aadhaar' },
    { name: 'PAN Verification', status: 'verified', timestamp: '2023-11-20 10:46 AM', officer: 'Auto-System', doc: 'pan' },
    { name: 'Tax Receipt Verification', status: 'pending', timestamp: '--', officer: '--', doc: 'tax' },
  ];

  return (
    <div className='card bg-white border border-slate-200'>
      <div className='flex items-center gap-2 mb-4 border-b pb-3 border-slate-100'>
        <Search className='w-5 h-5 text-blue-600' />
        <h3 className='font-semibold text-slate-800 text-lg'>Government Verification</h3>
      </div>
      
      <div className='space-y-4'>
        {verifications.map((item, index) => (
          <div key={index} className='border border-slate-100 rounded-lg p-4 bg-slate-50'>
            <div className='flex justify-between items-start mb-3'>
              <div>
                <h4 className='font-semibold text-slate-700'>{item.name}</h4>
                <div className='flex items-center gap-3 mt-1 text-xs text-slate-500'>
                   <span className='flex items-center gap-1'><Clock className='w-3 h-3'/> {item.timestamp}</span>
                   <span className='flex items-center gap-1'><ExternalLink className='w-3 h-3'/> By: {item.officer}</span>
                </div>
              </div>
              <div>
                {item.status === 'verified' && (
                   <span className='inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700'>
                     <CheckCircle className='w-3 h-3' /> Verified
                   </span>
                )}
                {item.status === 'pending' && (
                   <span className='inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700'>
                     <Clock className='w-3 h-3' /> Pending
                   </span>
                )}
                 {item.status === 'failed' && (
                   <span className='inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700'>
                     <XCircle className='w-3 h-3' /> Failed
                   </span>
                )}
              </div>
            </div>
            
            <div className='bg-white border border-dashed border-slate-300 rounded p-4 text-center h-24 flex flex-col items-center justify-center text-slate-400 text-sm'>
               [ Screenshot Placeholder for {item.name} ]
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default GovVerification;
'''
with open('src/pages/GovVerification.jsx', 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n')
print('GovVerification.jsx written')
