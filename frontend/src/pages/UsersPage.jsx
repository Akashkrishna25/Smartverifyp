import React from 'react';
import { Users } from 'lucide-react';

export default function UsersPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2.5">
            <Users className="w-6 h-6 text-primary-600" />
            Users
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage system users and permissions.
          </p>
        </div>
      </div>
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 text-center text-slate-500">
        User management coming soon.
      </div>
    </div>
  );
}
