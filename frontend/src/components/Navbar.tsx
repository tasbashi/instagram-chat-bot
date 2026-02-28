import { NavLink, useNavigate } from 'react-router-dom';
import { Bot, Calendar, MessageSquare, LogOut, Sun, Moon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export function Navbar() {
    const { user, logout } = useAuth();
    const { theme, toggle } = useTheme();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const initials = user?.full_name
        ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase()
        : user?.email?.[0]?.toUpperCase() || '?';

    const linkClass = ({ isActive }: { isActive: boolean }) =>
        `relative flex items-center gap-sm px-md py-sm rounded-md text-sm font-medium transition-all duration-150 ${isActive
            ? 'text-text-primary bg-bg-tertiary after:absolute after:bottom-[-1px] after:left-md after:right-md after:h-0.5 after:bg-gradient-to-r after:from-accent-purple after:via-accent-pink after:to-accent-orange after:rounded-full'
            : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
        }`;

    return (
        <nav className="sticky top-0 z-100 flex items-center justify-between px-xl h-16 bg-bg-primary/80 backdrop-blur-[20px] backdrop-saturate-[180%] border-b border-border-subtle">
            <div className="flex items-center gap-sm font-bold text-[1.1rem] tracking-tight">
                <div className="w-7 h-7 rounded-sm bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center text-sm">🤖</div>
                <span>InstaBot</span>
            </div>

            <div className="flex gap-xs">
                <NavLink to="/agents" className={linkClass}>
                    <Bot size={16} />
                    <span>Agents</span>
                </NavLink>
                <NavLink to="/appointments" className={linkClass}>
                    <Calendar size={16} />
                    <span>Appointments</span>
                </NavLink>
                <NavLink to="/chat-history" className={linkClass}>
                    <MessageSquare size={16} />
                    <span>Chat History</span>
                </NavLink>
            </div>

            <div className="flex items-center gap-md">
                <button
                    className="text-text-secondary hover:bg-bg-tertiary hover:text-text-primary p-1.5 rounded-md transition-all duration-150"
                    onClick={toggle}
                    title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                    {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                </button>
                <div className="w-[34px] h-[34px] rounded-full bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center text-[0.8rem] font-semibold text-white">{initials}</div>
                <button className="text-text-secondary hover:bg-bg-tertiary hover:text-text-primary p-1.5 rounded-md transition-all duration-150" onClick={handleLogout} title="Logout">
                    <LogOut size={16} />
                </button>
            </div>
        </nav>
    );
}
