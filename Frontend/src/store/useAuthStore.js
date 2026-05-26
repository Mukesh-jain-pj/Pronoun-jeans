import { create } from 'zustand';
import api from '../api/axios';
import { jwtDecode } from 'jwt-decode';

const decodeToken = (token) => {
  try {
    return jwtDecode(token);
  } catch {
    return null;
  }
};

const getInitialAuthState = () => {
  const token = localStorage.getItem('accessToken');
  if (!token) return { user: null, isAuthenticated: false, isAgent: false };
  const decoded = decodeToken(token);
  if (!decoded || decoded.exp * 1000 < Date.now()) {
    localStorage.clear();
    return { user: null, isAuthenticated: false, isAgent: false };
  }
  return { user: decoded, isAuthenticated: true, isAgent: decoded.is_agent ?? false };
};

export const useAuthStore = create((set, get) => ({
  ...getInitialAuthState(),

  initAuth: () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      set({ user: null, isAuthenticated: false, isAgent: false });
      return;
    }
    const decoded = decodeToken(token);
    if (!decoded || decoded.exp * 1000 < Date.now()) {
      localStorage.clear();
      set({ user: null, isAuthenticated: false, isAgent: false });
      return;
    }
    set({
      user:            decoded,
      isAuthenticated: true,
      isAgent:         decoded.is_agent ?? false,
    });
  },

  login: async (email, password) => {
    const res     = await api.post('auth/token/', { email, password });
    localStorage.setItem('accessToken',  res.data.access);
    localStorage.setItem('refreshToken', res.data.refresh);
    const decoded = decodeToken(res.data.access);
    set({
      user:            decoded,
      isAuthenticated: true,
      isAgent:         decoded?.is_agent ?? false,
    });
    return decoded;
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) {
      try {
        await api.post('auth/logout/', { refresh: refreshToken });
      } catch {
        // always clear locally
      }
    }
    localStorage.clear();
    set({ user: null, isAuthenticated: false, isAgent: false });
    window.location.replace('/login');
  },
}));