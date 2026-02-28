import { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { auth as authApi } from '../lib/api';

export function VerifyEmailPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const { verifyEmail } = useAuth();

    const email = (location.state as { email?: string })?.email || '';

    const [code, setCode] = useState<string[]>(Array(6).fill(''));
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);
    const [resendMessage, setResendMessage] = useState('');
    const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

    // Redirect if no email in state
    useEffect(() => {
        if (!email) navigate('/register', { replace: true });
    }, [email, navigate]);

    // Resend cooldown timer
    useEffect(() => {
        if (resendCooldown <= 0) return;
        const timer = setTimeout(() => setResendCooldown(c => c - 1), 1000);
        return () => clearTimeout(timer);
    }, [resendCooldown]);

    const handleChange = (index: number, value: string) => {
        if (!/^\d*$/.test(value)) return; // digits only

        const next = [...code];
        next[index] = value.slice(-1);
        setCode(next);
        setError('');

        if (value && index < 5) {
            inputsRef.current[index + 1]?.focus();
        }

        // Auto-submit when all 6 digits filled
        const fullCode = next.join('');
        if (fullCode.length === 6 && next.every(d => d !== '')) {
            handleSubmit(fullCode);
        }
    };

    const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
        if (e.key === 'Backspace' && !code[index] && index > 0) {
            inputsRef.current[index - 1]?.focus();
        }
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
        if (!pasted) return;

        const next = [...code];
        for (let i = 0; i < 6; i++) {
            next[i] = pasted[i] || '';
        }
        setCode(next);
        setError('');

        if (pasted.length === 6) {
            handleSubmit(pasted);
        } else {
            inputsRef.current[Math.min(pasted.length, 5)]?.focus();
        }
    };

    const handleSubmit = async (fullCode?: string) => {
        const codeStr = fullCode || code.join('');
        if (codeStr.length !== 6) {
            setError('Please enter all 6 digits');
            return;
        }

        setLoading(true);
        setError('');

        try {
            await verifyEmail(email, codeStr);
            navigate('/agents', { replace: true });
        } catch (err: any) {
            setError(err.message || 'Verification failed');
            setCode(Array(6).fill(''));
            inputsRef.current[0]?.focus();
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        if (resendCooldown > 0) return;
        setResendMessage('');
        setError('');

        try {
            await authApi.resendCode({ email });
            setResendCooldown(60);
            setResendMessage('New code sent!');
            setCode(Array(6).fill(''));
            inputsRef.current[0]?.focus();
        } catch (err: any) {
            setError(err.message || 'Failed to resend code');
        }
    };

    if (!email) return null;

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg-primary p-xl">
            <div className="w-full max-w-[400px] animate-slide-up">
                {/* Logo */}
                <div className="flex items-center gap-sm text-[1.3rem] font-bold mb-2xl justify-center">
                    <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center text-lg">🤖</div>
                    InstaBot
                </div>

                {/* Header */}
                <h2 className="text-2xl font-bold text-center mb-xs tracking-tight">Check your email</h2>
                <p className="text-center text-text-secondary text-sm mb-lg">
                    We sent a 6-digit code to <span className="text-text-primary font-medium">{email}</span>
                </p>

                {/* Error */}
                {error && (
                    <div className="bg-error/10 border border-error/20 rounded-md p-md mb-md text-error text-sm text-center">
                        {error}
                    </div>
                )}

                {/* Success message */}
                {resendMessage && (
                    <div className="bg-success/10 border border-success/20 rounded-md p-md mb-md text-success text-sm text-center">
                        {resendMessage}
                    </div>
                )}

                {/* Code inputs */}
                <div className="flex justify-center gap-2.5 mb-lg" onPaste={handlePaste}>
                    {code.map((digit, i) => (
                        <input
                            key={i}
                            ref={el => { inputsRef.current[i] = el; }}
                            id={`verify-digit-${i}`}
                            type="text"
                            inputMode="numeric"
                            maxLength={1}
                            value={digit}
                            onChange={e => handleChange(i, e.target.value)}
                            onKeyDown={e => handleKeyDown(i, e)}
                            className={`w-12 h-14 text-center text-xl font-bold rounded-lg border transition-all duration-150 outline-none bg-bg-tertiary text-text-primary
                                ${digit
                                    ? 'border-accent-purple shadow-[0_0_0_3px_rgba(139,92,246,0.15)]'
                                    : 'border-border-default'
                                }
                                focus:border-accent-purple focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)]`}
                            disabled={loading}
                            autoFocus={i === 0}
                        />
                    ))}
                </div>

                {/* Verify button */}
                <button
                    id="verify-submit"
                    onClick={() => handleSubmit()}
                    disabled={loading || code.join('').length !== 6}
                    className="w-full inline-flex items-center justify-center gap-sm py-3 rounded-md text-sm font-medium bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange text-white shadow-sm hover:shadow-glow hover:-translate-y-px transition-all duration-150 disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
                >
                    {loading ? (
                        <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Verifying...
                        </span>
                    ) : (
                        'Verify email'
                    )}
                </button>

                {/* Resend */}
                <div className="text-center mt-lg text-sm text-text-secondary">
                    Didn't receive the code?{' '}
                    {resendCooldown > 0 ? (
                        <span className="text-text-tertiary">Resend in {resendCooldown}s</span>
                    ) : (
                        <button
                            onClick={handleResend}
                            className="text-accent-purple font-medium hover:underline bg-transparent border-none cursor-pointer"
                        >
                            Resend code
                        </button>
                    )}
                </div>

                {/* Back to register */}
                <div className="text-center mt-md text-sm text-text-secondary">
                    Wrong email? <Link to="/register" className="text-accent-purple font-medium hover:underline">Go back</Link>
                </div>
            </div>
        </div>
    );
}
