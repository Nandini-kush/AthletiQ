import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { checkHealth } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Activity, Play } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [backendStatus, setBackendStatus] = useState<string>('Checking...');

  useEffect(() => {
    checkHealth()
      .then((data) => setBackendStatus(data.status === 'ok' ? 'Backend Connected ✅' : 'Status Unknown'))
      .catch(() => setBackendStatus('Backend Disconnected ❌'));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          {user && <p className="text-gray-500">Welcome back, <span className="font-semibold text-blue-600">{user.full_name}</span></p>}
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${backendStatus.includes('Connected') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {backendStatus}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Sessions</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">0</p>
        </Card>
        <Card className="p-6">
          <h3 className="text-sm font-medium text-gray-500">Avg Performance Score</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">—</p>
        </Card>
        <Card className="p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Reps</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">0</p>
        </Card>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Recent Activity</h2>
        </div>
        <div className="text-center text-gray-500 py-8">
          <Activity className="mx-auto h-10 w-10 text-gray-300 mb-3" />
          <p>No workout sessions recorded yet.</p>
          <p className="text-sm mt-1">Head over to Live Analysis to start your first session!</p>
          <Link to="/live-analysis">
            <Button className="mt-4" size="sm">
              <Play className="h-4 w-4 mr-2" /> Start Analysis
            </Button>
          </Link>
        </div>
      </Card>
    </div>
  );
};
