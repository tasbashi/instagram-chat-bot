import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function RegisterPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await register(email, password, fullName || undefined);
            navigate('/agents');
        } catch (err: any) {
            setError(err.message || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    const inputClass = "w-full py-2.5 px-3.5 bg-bg-tertiary border border-border-default rounded-md text-text-primary text-sm transition-all duration-150 outline-none focus:border-accent-purple focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] placeholder:text-text-tertiary";

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg-primary p-xl">
            <div className="w-full max-w-[400px] animate-slide-up">
                <div className="flex items-center gap-sm text-[1.3rem] font-bold mb-2xl justify-center">
                    <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center text-lg">🤖</div>
                    InstaBot
                </div>

                <h2 className="text-2xl font-bold text-center mb-xs tracking-tight">Create account</h2>
                <p className="text-center text-text-secondary text-sm mb-xl">Set up your Instagram chatbot in minutes</p>

                {error && (
                    <div className="bg-error/10 border border-error/20 rounded-md p-md mb-md text-error text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="mb-md">
                        <label className="block text-[0.8rem] font-medium text-text-secondary mb-xs uppercase tracking-wider">Full Name</label>
                        <input id="register-name" className={inputClass} type="text" placeholder="John Doe" value={fullName} onChange={e => setFullName(e.target.value)} />
                    </div>
                    <div className="mb-md">
                        <label className="block text-[0.8rem] font-medium text-text-secondary mb-xs uppercase tracking-wider">Email</label>
                        <input id="register-email" className={inputClass} type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
                    </div>
                    <div className="mb-md">
                        <label className="block text-[0.8rem] font-medium text-text-secondary mb-xs uppercase tracking-wider">Password</label>
                        <input id="register-password" className={inputClass} type="password" placeholder="Minimum 6 characters" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
                    </div>

                    <button id="register-submit" className="w-full inline-flex items-center justify-center gap-sm py-3 rounded-md text-sm font-medium bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange text-white shadow-sm hover:shadow-glow hover:-translate-y-px transition-all duration-150 mt-sm" type="submit" disabled={loading}>
                        {loading ? 'Creating account...' : 'Create account'}
                    </button>
                </form>

                <div className="text-center mt-lg text-sm text-text-secondary">
                    Already have an account? <Link to="/login" className="text-accent-purple font-medium hover:underline">Sign in</Link>
                </div>
            </div>
        </div>
    );
}
