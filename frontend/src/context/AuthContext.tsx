import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { auth, type User } from '../lib/api';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, fullName?: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            auth.me().then(setUser).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (email: string, password: string) => {
        const res = await auth.login({ email, password });
        localStorage.setItem('token', res.access_token);
        const me = await auth.me();
        setUser(me);
    };

    const register = async (email: string, password: string, fullName?: string) => {
        const res = await auth.register({ email, password, full_name: fullName });
        localStorage.setItem('token', res.access_token);
        const me = await auth.me();
        setUser(me);
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
