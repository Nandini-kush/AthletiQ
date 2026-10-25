const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

export const checkHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json();
};

export const login = async (data: { email: string; password: string }) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Login failed');
  }
  return response.json();
};

export const register = async (data: { full_name: string; email: string; password: string }) => {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Registration failed');
  }
  return response.json();
};

export const getCurrentUser = async () => {
  const response = await fetch(`${API_BASE_URL}/api/users/me`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error('Not authenticated');
  return response.json();
};

export interface AthleteProfileData {
  age?: number | null;
  gender?: string | null;
  height?: number | null;
  weight?: number | null;
  sport?: string | null;
  experience_level?: string | null;
}

export const getProfile = async () => {
  const response = await fetch(`${API_BASE_URL}/api/athletes/profile`, {
    headers: getHeaders()
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to fetch profile');
  }
  return response.json();
};

export const createProfile = async (data: AthleteProfileData) => {
  const response = await fetch(`${API_BASE_URL}/api/athletes/profile`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to create profile');
  }
  return response.json();
};

export const updateProfile = async (data: AthleteProfileData) => {
  const response = await fetch(`${API_BASE_URL}/api/athletes/profile`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to update profile');
  }
  return response.json();
};

export interface ExerciseSessionData {
  exercise_name: string;
  started_at: string;
  ended_at: string;
  duration: number;
  total_repetitions?: number;
}

export const getSessions = async () => {
  const response = await fetch(`${API_BASE_URL}/api/sessions/`, {
    headers: getHeaders()
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to fetch sessions');
  }
  return response.json();
};

export const getSession = async (sessionId: number) => {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
    headers: getHeaders()
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to fetch session');
  }
  return response.json();
};

export const createSession = async (data: ExerciseSessionData) => {
  const response = await fetch(`${API_BASE_URL}/api/sessions/`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to create session');
  }
  return response.json();
};
