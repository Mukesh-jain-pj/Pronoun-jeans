import React, { useEffect, useState } from 'react';
import { IndianRupee, TrendingUp, CheckCircle2, Clock, Loader } from 'lucide-react';
import api from '../../api/axios';
import { useAuthStore } from '../../store/useAuthStore';

const fmt = (val) =>
  `₹${parseFloat(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const MetricCard = ({ icon: Icon, label, value, iconBg, iconColor, loading }) => (
  <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-white/5 p-6 shadow-sm">
    <div className="flex items-start justify-between mb-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${iconBg}`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
    </div>
    {loading ? (
      <div className="space-y-2 animate-pulse">
        <div className="h-7 w-28 bg-gray-200 dark:bg-zinc-700 rounded" />
        <div className="h-3 w-20 bg-gray-100 dark:bg-zinc-800 rounded" />
      </div>
    ) : (
      <>
        <p className="text-2xl font-black text-gray-900 dark:text-zinc-100">{value}</p>
        <p className="text-xs font-semibold text-gray-500 dark:text-zinc-400 uppercase tracking-widest mt-1">{label}</p>
      </>
    )}
  </div>
);

const AgentDashboard = () => {
  const { user } = useAuthStore();
  const [ledger, setLedger]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    api.get('orders/agent/ledger/')
      .then(res => setLedger(res.data))
      .catch(() => setError('Failed to load ledger data.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="text-accent text-xs font-black uppercase tracking-widest mb-1">Agent Portal</p>
        <h1 className="text-2xl font-black text-gray-900 dark:text-zinc-100">
          Welcome{user?.email ? `, ${user.email.split('@')[0]}` : ''}
        </h1>
        <p className="text-gray-500 dark:text-zinc-400 text-sm mt-1">
          Here's your commission summary at a glance.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/25 text-red-600 dark:text-red-400 text-sm px-4 py-3 rounded-xl mb-6">
          {error}
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <MetricCard
          icon={TrendingUp}
          label="Total Earned"
          value={loading ? '' : fmt(ledger?.total_earned)}
          iconBg="bg-green-50 dark:bg-green-500/10"
          iconColor="text-green-600 dark:text-green-400"
          loading={loading}
        />
        <MetricCard
          icon={CheckCircle2}
          label="Total Paid"
          value={loading ? '' : fmt(ledger?.total_paid)}
          iconBg="bg-blue-50 dark:bg-blue-500/10"
          iconColor="text-blue-600 dark:text-blue-400"
          loading={loading}
        />
        <MetricCard
          icon={Clock}
          label="Balance Due"
          value={loading ? '' : fmt(ledger?.balance_due)}
          iconBg="bg-orange-50 dark:bg-orange-500/10"
          iconColor="text-orange-600 dark:text-orange-400"
          loading={loading}
        />
      </div>

      {/* Quick links */}
      <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-white/5 p-6 shadow-sm">
        <h2 className="text-gray-900 dark:text-zinc-100 font-bold text-sm mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'My Buyers',     to: '/agent/buyers'      },
            { label: 'Orders',        to: '/agent/orders'      },
            { label: 'Commissions',   to: '/agent/commissions' },
            { label: 'Sample Orders', to: '/agent/samples'     },
          ].map(({ label, to }) => (
            <a key={to} href={to}
              className="flex items-center justify-center text-center text-sm font-semibold text-gray-700 dark:text-zinc-300 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 transition-colors">
              {label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;