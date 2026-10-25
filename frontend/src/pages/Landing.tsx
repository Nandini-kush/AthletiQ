import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/Button';
import { Activity } from 'lucide-react';

export const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-white flex flex-col justify-center items-center text-center p-4">
      <Activity className="h-16 w-16 text-blue-600 mb-6" />
      <h1 className="text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
        AthletiQ
      </h1>
      <p className="text-xl text-gray-500 max-w-2xl mb-8">
        AI-Based Real-Time Athlete Performance, Strength, and Biomechanical Analysis System.
      </p>
      <div className="flex space-x-4">
        <Link to="/login">
          <Button variant="outline" size="lg">Log In</Button>
        </Link>
        <Link to="/dashboard">
          <Button variant="primary" size="lg">Go to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
};
