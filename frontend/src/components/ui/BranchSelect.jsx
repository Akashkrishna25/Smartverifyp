import React from 'react';
import { BRANCHES } from '../../utils/constants';

/**
 * Reusable branch selector with Other Branch free-text support.
 */
export default function BranchSelect({ value, onChange, required = false }) {
  const isKnown = BRANCHES.includes(value) || value === '';
  const sv = isKnown ? value : '__other__';

  const handleSelect = (e) => {
    const v = e.target.value;
    if (v === '__other__') onChange('__other__');
    else onChange(v);
  };

  return (
    <div className='space-y-2'>
      <select required={required} value={sv} onChange={handleSelect} className='input'>
        <option value=''>Select Branch</option>
        {BRANCHES.map((b) => (<option key={b} value={b}>{b}</option>))}
        <option value='__other__'>Other Branch</option>
      </select>
      {(value === '__other__' || (!isKnown && value !== '')) && (
        <input
          type='text'
          required={required}
          placeholder='Enter branch name'
          value={value === '__other__' ? '' : value}
          onChange={(e) => onChange(e.target.value)}
          className='input'
        />
      )}
    </div>
  );
}
