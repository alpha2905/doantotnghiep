import axios, { AxiosInstance, AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_URL } from '../constants/theme';

const TOKEN_KEY = 'auth_token';

export const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  async (config) => {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (email: string, password: string) => {
    const res = await api.post('/api/auth/login', { email, password });
    return res.data;
  },
  register: async (email: string, password: string, fullName: string) => {
    const res = await api.post('/api/auth/register', { email, password, full_name: fullName });
    return res.data;
  },
  me: async () => {
    const res = await api.get('/api/auth/me');
    return res.data;
  },
};

export const searchApi = {
  search: async (name: string) => {
    const res = await api.get('/api/search', { params: { name } });
    return res.data;
  },
  compare: async (name: string) => {
    const res = await api.get('/api/compare', { params: { name } });
    return res.data;
  },
};

export const favoriteApi = {
  getFavorites: async () => {
    const res = await api.get('/api/favorites');
    return res.data;
  },
  addFavorite: async (product: any) => {
    const res = await api.post('/api/favorites', product);
    return res.data;
  },
  removeFavorite: async (name: string, platform: string) => {
    const res = await api.delete('/api/favorites', { params: { name, platform } });
    return res.data;
  },
};

export const notificationApi = {
  getNotifications: async () => {
    const res = await api.get('/api/notifications');
    return res.data;
  },
  markRead: async (keys: string[] | { all: boolean }) => {
    const res = await api.post('/api/notifications/mark-read', keys);
    return res.data;
  },
};

export const tokenApi = {
  registerFcmToken: async (token: string) => {
    const res = await api.post('/api/fcm-token', { token });
    return res.data;
  },
};

export const storage = {
  getToken: async (): Promise<string | null> => {
    return await SecureStore.getItemAsync(TOKEN_KEY);
  },
  setToken: async (token: string): Promise<void> => {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  },
  removeToken: async (): Promise<void> => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  },
};
