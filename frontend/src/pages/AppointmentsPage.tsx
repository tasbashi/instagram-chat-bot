import { useEffect, useState, useMemo, useCallback } from 'react';
import { Calendar, Plus, X, CheckCircle, XCircle, Clock, LayoutGrid, List, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { appointments, type Appointment } from '../lib/api';

/* ── Shared class strings ──────────────────────────────────────── */

const inputClass = "w-full py-2.5 px-3.5 bg-bg-tertiary border border-border-default rounded-md text-text-primary text-sm transition-all duration-150 outline-none focus:border-accent-purple focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] placeholder:text-text-tertiary";
const labelClass = "block text-[0.8rem] font-medium text-text-secondary mb-xs uppercase tracking-wider";
const btnPrimary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange text-white shadow-sm hover:shadow-glow hover:-translate-y-px transition-all duration-150";
const btnSecondary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-bg-tertiary border border-border-default text-text-primary hover:bg-bg-card-hover hover:border-border-strong transition-all duration-150";
const btnGhost = "inline-flex items-center justify-center gap-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-all duration-150";
const btnDanger = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-error/10 text-error border border-error/20 hover:bg-error/20 transition-all duration-150";
const btnSm = "px-3 py-1.5 text-[0.8rem]";

/* ── Constants ─────────────────────────────────────────────────── */

const START_HOUR = 8;
const END_HOUR = 21;
const SLOT_HEIGHT = 48; // px per 30-min slot
const HOUR_HEIGHT = SLOT_HEIGHT * 2; // px per hour
const TOTAL_HOURS = END_HOUR - START_HOUR;

type ViewMode = 'week' | 'list';

/* ── Utilities ─────────────────────────────────────────────────── */

function getWeekDays(baseDate: Date): Date[] {
    const d = new Date(baseDate);
    const day = d.getDay();
    const monday = new Date(d);
    monday.setDate(d.getDate() - ((day + 6) % 7)); // Monday start
    const days: Date[] = [];
    for (let i = 0; i < 7; i++) {
        const dd = new Date(monday);
        dd.setDate(monday.getDate() + i);
        days.push(dd);
    }
    return days;
}

function fmt(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isSameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function parseTime(timeStr: string): { hour: number; minute: number } {
    const [h, m] = timeStr.split(':').map(Number);
    return { hour: h || 0, minute: m || 0 };
}

function getTopOffset(timeStr: string): number {
    const { hour, minute } = parseTime(timeStr);
    return ((hour - START_HOUR) * HOUR_HEIGHT) + ((minute / 60) * HOUR_HEIGHT);
}

function getBlockHeight(duration: number): number {
    return Math.max((duration / 60) * HOUR_HEIGHT, 24);
}

const statusColors: Record<string, { bg: string; border: string; text: string }> = {
    confirmed: { bg: 'bg-accent-purple/12', border: 'border-l-accent-purple', text: 'text-accent-purple' },
    completed: { bg: 'bg-success/12', border: 'border-l-success', text: 'text-success' },
    cancelled: { bg: 'bg-error/8', border: 'border-l-error', text: 'text-error' },
    pending: { bg: 'bg-warning/12', border: 'border-l-warning', text: 'text-warning' },
};
const defaultColor = { bg: 'bg-accent-blue/12', border: 'border-l-accent-blue', text: 'text-accent-blue' };

/* ══════════════════════════════════════════════════════════════════
   Main Page
   ══════════════════════════════════════════════════════════════════ */

export function AppointmentsPage() {
    const [list, setList] = useState<Appointment[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('');
    const [showCreate, setShowCreate] = useState(false);
    const [view, setView] = useState<ViewMode>('week');
    const [baseDate, setBaseDate] = useState(() => new Date());
    const [search, setSearch] = useState('');

    useEffect(() => { loadAppointments(); }, [filter]);

    const loadAppointments = async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (filter) params.status = filter;
            const data = await appointments.list(params);
            setList(data);
        } catch { /* empty */ }
        setLoading(false);
    };

    const handleCancel = async (id: string) => {
        try {
            await appointments.cancel(id, 'Cancelled by admin');
            loadAppointments();
        } catch { /* empty */ }
    };

    const handleComplete = async (id: string) => {
        try {
            await appointments.complete(id);
            loadAppointments();
        } catch { /* empty */ }
    };

    const weekDays = useMemo(() => getWeekDays(baseDate), [baseDate]);
    const today = useMemo(() => new Date(), []);

    const prevWeek = () => setBaseDate(d => { const n = new Date(d); n.setDate(d.getDate() - 7); return n; });
    const nextWeek = () => setBaseDate(d => { const n = new Date(d); n.setDate(d.getDate() + 7); return n; });
    const goToday = () => setBaseDate(new Date());

    const goToDate = useCallback((d: Date) => setBaseDate(d), []);

    const weekRange = useMemo(() => {
        const first = weekDays[0];
        const last = weekDays[6];
        const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
        const yearOpts: Intl.DateTimeFormatOptions = { ...opts, year: 'numeric' };
        if (first.getFullYear() !== last.getFullYear()) {
            return `${first.toLocaleDateString('en-US', yearOpts)} – ${last.toLocaleDateString('en-US', yearOpts)}`;
        }
        return `${first.toLocaleDateString('en-US', opts)} – ${last.toLocaleDateString('en-US', yearOpts)}`;
    }, [weekDays]);

    const stats = useMemo(() => ({
        total: list.length,
        confirmed: list.filter(a => a.status === 'confirmed').length,
        completed: list.filter(a => a.status === 'completed').length,
        cancelled: list.filter(a => a.status === 'cancelled').length,
    }), [list]);

    const filteredList = useMemo(() => {
        if (!search) return list;
        const q = search.toLowerCase();
        return list.filter(a =>
            (a.customer_name?.toLowerCase().includes(q)) ||
            a.customer_ig_id.toLowerCase().includes(q) ||
            (a.service_type?.toLowerCase().includes(q))
        );
    }, [list, search]);

    const todayAppointments = useMemo(() => {
        const todayStr = fmt(today);
        return list.filter(a => a.appointment_date === todayStr).sort((a, b) => a.appointment_time.localeCompare(b.appointment_time));
    }, [list, today]);

    return (
        <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden">
            {/* ── Top header bar ─────────────────────────────────── */}
            <div className="flex items-center justify-between px-lg py-md border-b border-border-subtle bg-bg-primary shrink-0">
                <div className="flex items-center gap-md">
                    <h1 className="text-xl font-bold tracking-tight">Appointments</h1>
                    {view === 'week' && (
                        <div className="flex items-center gap-sm ml-md">
                            <button className={`${btnSecondary} ${btnSm}`} onClick={goToday}>Today</button>
                            <button className={`${btnGhost} p-1.5 rounded-md`} onClick={prevWeek}><ChevronLeft size={18} /></button>
                            <button className={`${btnGhost} p-1.5 rounded-md`} onClick={nextWeek}><ChevronRight size={18} /></button>
                            <span className="text-sm font-medium text-text-primary ml-xs">{weekRange}</span>
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-sm">
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                        <input
                            className="py-1.5 pl-8 pr-3 bg-bg-tertiary border border-border-default rounded-md text-text-primary text-sm w-[200px] outline-none focus:border-accent-purple transition-all duration-150 placeholder:text-text-tertiary"
                            placeholder="Search..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                    </div>
                    <div className="flex bg-bg-tertiary rounded-md p-[3px] gap-0.5">
                        <button className={`flex items-center justify-center p-1.5 px-2.5 rounded-sm transition-all duration-150 ${view === 'week' ? 'bg-bg-secondary text-text-primary shadow-[0_1px_4px_rgba(0,0,0,0.2)]' : 'text-text-tertiary hover:text-text-secondary'}`} onClick={() => setView('week')} title="Week view">
                            <LayoutGrid size={16} />
                        </button>
                        <button className={`flex items-center justify-center p-1.5 px-2.5 rounded-sm transition-all duration-150 ${view === 'list' ? 'bg-bg-secondary text-text-primary shadow-[0_1px_4px_rgba(0,0,0,0.2)]' : 'text-text-tertiary hover:text-text-secondary'}`} onClick={() => setView('list')} title="List view">
                            <List size={16} />
                        </button>
                    </div>
                    <button className={btnPrimary} onClick={() => setShowCreate(true)}>
                        <Plus size={16} /> New
                    </button>
                </div>
            </div>

            {/* ── Main body ──────────────────────────────────────── */}
            {view === 'week' ? (
                <div className="flex flex-1 overflow-hidden">
                    {/* Left Sidebar */}
                    <div className="w-[260px] shrink-0 border-r border-border-subtle bg-bg-primary overflow-y-auto p-md flex flex-col gap-lg">
                        <MiniCalendar baseDate={baseDate} today={today} onSelectDate={goToDate} />

                        {/* Today's appointments */}
                        <div>
                            <h3 className="text-[0.75rem] font-semibold uppercase tracking-wider text-text-tertiary mb-sm">Today's Appointments</h3>
                            {todayAppointments.length === 0 ? (
                                <p className="text-xs text-text-tertiary">No appointments today</p>
                            ) : (
                                <div className="flex flex-col gap-xs">
                                    {todayAppointments.map(a => {
                                        const c = statusColors[a.status] || defaultColor;
                                        return (
                                            <div key={a.id} className={`flex items-start gap-sm p-sm rounded-md ${c.bg} border-l-2 ${c.border}`}>
                                                <div className="min-w-0 flex-1">
                                                    <div className="text-[0.78rem] font-medium text-text-primary truncate">{[a.customer_name, a.customer_surname].filter(Boolean).join(' ') || a.customer_ig_id}</div>
                                                    <div className="text-[0.7rem] text-text-secondary">{a.appointment_time}{a.subject ? ` · ${a.subject}` : a.service_type ? ` · ${a.service_type}` : ''}</div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Stats */}
                        <div>
                            <h3 className="text-[0.75rem] font-semibold uppercase tracking-wider text-text-tertiary mb-sm">Overview</h3>
                            <div className="grid grid-cols-2 gap-xs">
                                {([
                                    { label: 'Total', value: stats.total, color: 'text-text-primary' },
                                    { label: 'Confirmed', value: stats.confirmed, color: 'text-accent-purple' },
                                    { label: 'Completed', value: stats.completed, color: 'text-success' },
                                    { label: 'Cancelled', value: stats.cancelled, color: 'text-error' },
                                ] as const).map(s => (
                                    <div key={s.label} className="bg-bg-tertiary rounded-md p-sm text-center">
                                        <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
                                        <div className="text-[0.65rem] text-text-tertiary uppercase tracking-wider">{s.label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Weekly Time Grid */}
                    <WeeklyTimeGrid
                        weekDays={weekDays}
                        today={today}
                        appointments={filteredList}
                        onComplete={handleComplete}
                        onCancel={handleCancel}
                    />
                </div>
            ) : (
                /* ── List View ──────────────────────────────────── */
                <div className="flex-1 overflow-y-auto p-lg">
                    <div className="max-w-[1200px] mx-auto">
                        <div className="flex gap-sm mb-md">
                            {['', 'confirmed', 'completed', 'cancelled'].map(f => (
                                <button
                                    key={f}
                                    className={`${btnSm} ${filter === f ? btnPrimary : btnSecondary} capitalize`}
                                    onClick={() => setFilter(f)}
                                >
                                    {f || 'All'}
                                </button>
                            ))}
                        </div>

                        <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden">
                            {loading ? (
                                <div className="p-xl text-center text-text-secondary">Loading...</div>
                            ) : filteredList.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-3xl px-xl text-center">
                                    <div className="w-16 h-16 rounded-lg bg-bg-tertiary flex items-center justify-center mb-md text-text-tertiary"><Calendar size={28} /></div>
                                    <h3 className="text-lg font-semibold mb-xs">No appointments</h3>
                                    <p className="text-text-secondary text-sm max-w-[360px]">Appointments booked via the chatbot will appear here</p>
                                </div>
                            ) : (
                                <table className="w-full border-collapse">
                                    <thead>
                                        <tr>
                                            {['Customer', 'Date', 'Time', 'Subject', 'Service', 'Source', 'Status', 'Actions'].map(h => (
                                                <th key={h} className="px-md py-sm text-left text-xs font-semibold text-text-tertiary uppercase tracking-wider border-b border-border-subtle">{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredList.map(appt => (
                                            <tr key={appt.id} className="transition-colors duration-150 hover:bg-bg-card-hover">
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">
                                                    <div className="font-medium">{[appt.customer_name, appt.customer_surname].filter(Boolean).join(' ') || appt.customer_ig_id}</div>
                                                    {appt.customer_name && <div className="text-xs text-text-tertiary">{appt.customer_ig_id}</div>}
                                                </td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">{new Date(appt.appointment_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">{appt.appointment_time}</td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">{appt.subject || '—'}</td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">{appt.service_type || '—'}</td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">
                                                    <StatusBadge status={appt.created_via === 'chatbot' ? 'completed' : 'ready'} label={appt.created_via} />
                                                </td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">
                                                    <StatusBadge status={appt.status} />
                                                </td>
                                                <td className="p-md text-sm border-b border-border-subtle align-middle">
                                                    {appt.status === 'confirmed' && (
                                                        <div className="flex gap-xs">
                                                            <button className={`${btnSecondary} ${btnSm}`} onClick={() => handleComplete(appt.id)} title="Complete"><CheckCircle size={14} /></button>
                                                            <button className={`${btnDanger} ${btnSm}`} onClick={() => handleCancel(appt.id)} title="Cancel"><XCircle size={14} /></button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {showCreate && <CreateAppointmentModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); loadAppointments(); }} />}
        </div>
    );
}

/* ══════════════════════════════════════════════════════════════════
   Weekly Time Grid
   ══════════════════════════════════════════════════════════════════ */

function WeeklyTimeGrid({ weekDays, today, appointments: allAppts, onComplete, onCancel }: {
    weekDays: Date[];
    today: Date;
    appointments: Appointment[];
    onComplete: (id: string) => void;
    onCancel: (id: string) => void;
}) {
    const [hoveredAppt, setHoveredAppt] = useState<string | null>(null);

    // Group appointments by date string
    const apptsByDate = useMemo(() => {
        const map: Record<string, Appointment[]> = {};
        for (const a of allAppts) {
            if (!map[a.appointment_date]) map[a.appointment_date] = [];
            map[a.appointment_date].push(a);
        }
        return map;
    }, [allAppts]);

    // Current time indicator
    const [now, setNow] = useState(() => new Date());
    useEffect(() => {
        const timer = setInterval(() => setNow(new Date()), 60_000);
        return () => clearInterval(timer);
    }, []);

    const nowTop = useMemo(() => {
        const h = now.getHours();
        const m = now.getMinutes();
        if (h < START_HOUR || h >= END_HOUR) return -1;
        return ((h - START_HOUR) * HOUR_HEIGHT) + ((m / 60) * HOUR_HEIGHT);
    }, [now]);

    const isCurrentWeek = weekDays.some(d => isSameDay(d, today));

    const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

    const timeSlots: string[] = [];
    for (let h = START_HOUR; h < END_HOUR; h++) {
        timeSlots.push(`${String(h).padStart(2, '0')}:00`);
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* Day column headers */}
            <div className="flex shrink-0 border-b border-border-subtle bg-bg-primary">
                {/* Time gutter spacer */}
                <div className="w-[60px] shrink-0" />
                {weekDays.map((day, i) => {
                    const isToday = isSameDay(day, today);
                    return (
                        <div key={i} className="flex-1 flex flex-col items-center py-sm border-l border-border-subtle first:border-l-0">
                            <span className={`text-[0.65rem] font-semibold uppercase tracking-wider ${isToday ? 'text-accent-purple' : 'text-text-tertiary'}`}>{dayLabels[i]}</span>
                            <span className={`text-lg font-semibold leading-none mt-0.5 w-9 h-9 flex items-center justify-center rounded-full ${isToday ? 'bg-accent-purple text-white' : 'text-text-primary'}`}>
                                {day.getDate()}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Scrollable grid body */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden">
                <div className="flex relative" style={{ minHeight: `${TOTAL_HOURS * HOUR_HEIGHT}px` }}>
                    {/* Time labels gutter */}
                    <div className="w-[60px] shrink-0 relative">
                        {timeSlots.map((t, i) => (
                            <div
                                key={t}
                                className="absolute right-0 pr-sm text-[0.7rem] text-text-tertiary font-medium leading-none -translate-y-1/2"
                                style={{ top: `${i * HOUR_HEIGHT}px` }}
                            >
                                {t}
                            </div>
                        ))}
                    </div>

                    {/* Day columns */}
                    {weekDays.map((day, colIndex) => {
                        const dateStr = fmt(day);
                        const dayAppts = apptsByDate[dateStr] || [];
                        const isToday = isSameDay(day, today);

                        // Detect time overlaps for stacking
                        const positioned = layoutAppointments(dayAppts);

                        return (
                            <div
                                key={colIndex}
                                className={`flex-1 relative border-l border-border-subtle first:border-l-0 ${isToday ? 'bg-accent-purple/[0.03]' : ''}`}
                            >
                                {/* Horizontal hour lines */}
                                {timeSlots.map((_, i) => (
                                    <div
                                        key={i}
                                        className="absolute left-0 right-0 border-t border-border-subtle"
                                        style={{ top: `${i * HOUR_HEIGHT}px` }}
                                    />
                                ))}
                                {/* Half-hour lines */}
                                {timeSlots.map((_, i) => (
                                    <div
                                        key={`half-${i}`}
                                        className="absolute left-0 right-0 border-t border-border-subtle/40"
                                        style={{ top: `${i * HOUR_HEIGHT + SLOT_HEIGHT}px` }}
                                    />
                                ))}

                                {/* Appointment blocks */}
                                {positioned.map(({ appt, left, width }) => {
                                    const top = getTopOffset(appt.appointment_time);
                                    const height = getBlockHeight(appt.duration_minutes || 30);
                                    const c = statusColors[appt.status] || defaultColor;
                                    const isHovered = hoveredAppt === appt.id;

                                    if (top < 0) return null; // outside grid range

                                    return (
                                        <div
                                            key={appt.id}
                                            className={`absolute rounded-md border-l-[3px] ${c.border} ${c.bg} px-1.5 py-1 overflow-hidden cursor-pointer transition-all duration-100 hover:shadow-md hover:z-20 group ${isHovered ? 'z-20 shadow-md' : 'z-10'}`}
                                            style={{
                                                top: `${top}px`,
                                                height: `${height}px`,
                                                left: `${left}%`,
                                                width: `${width}%`,
                                                right: '2px',
                                            }}
                                            onMouseEnter={() => setHoveredAppt(appt.id)}
                                            onMouseLeave={() => setHoveredAppt(null)}
                                        >
                                            <div className={`text-[0.7rem] font-semibold ${c.text} leading-tight truncate`}>
                                                {appt.appointment_time}{appt.duration_minutes ? ` - ${endTime(appt.appointment_time, appt.duration_minutes)}` : ''}
                                            </div>
                                            <div className="text-[0.7rem] font-medium text-text-primary leading-tight truncate">
                                                {[appt.customer_name, appt.customer_surname].filter(Boolean).join(' ') || appt.customer_ig_id}
                                            </div>
                                            {height > 50 && appt.subject && (
                                                <div className="text-[0.65rem] text-text-secondary truncate mt-px">
                                                    ▸ {appt.subject}
                                                </div>
                                            )}

                                            {/* Hover actions */}
                                            {isHovered && appt.status === 'confirmed' && (
                                                <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        className="w-5 h-5 rounded bg-success/20 text-success flex items-center justify-center hover:bg-success/30"
                                                        onClick={e => { e.stopPropagation(); onComplete(appt.id); }}
                                                        title="Complete"
                                                    >
                                                        <CheckCircle size={11} />
                                                    </button>
                                                    <button
                                                        className="w-5 h-5 rounded bg-error/20 text-error flex items-center justify-center hover:bg-error/30"
                                                        onClick={e => { e.stopPropagation(); onCancel(appt.id); }}
                                                        title="Cancel"
                                                    >
                                                        <XCircle size={11} />
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}

                                {/* Current time indicator */}
                                {isToday && isCurrentWeek && nowTop >= 0 && (
                                    <div className="absolute left-0 right-0 z-30 pointer-events-none" style={{ top: `${nowTop}px` }}>
                                        <div className="relative">
                                            <div className="absolute -left-[5px] -top-[5px] w-[10px] h-[10px] rounded-full bg-error" />
                                            <div className="h-[2px] bg-error w-full" />
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

/* ── Overlap layout algorithm ──────────────────────────────────── */

function layoutAppointments(appts: Appointment[]): { appt: Appointment; left: number; width: number }[] {
    if (appts.length === 0) return [];

    const sorted = [...appts].sort((a, b) => a.appointment_time.localeCompare(b.appointment_time));
    const result: { appt: Appointment; left: number; width: number; end: number }[] = [];

    for (const appt of sorted) {
        const { hour, minute } = parseTime(appt.appointment_time);
        const startMin = hour * 60 + minute;
        const endMin = startMin + (appt.duration_minutes || 30);

        // Find overlapping column
        let col = 0;
        const overlapping = result.filter(r => r.end > startMin);
        const usedCols = new Set(overlapping.map(r => Math.round(r.left / (100 / (overlapping.length + 1)))));

        while (usedCols.has(col)) col++;

        result.push({ appt, left: 0, width: 100, end: endMin });
    }

    // Calculate columns for overlapping groups
    const groups: { appt: Appointment; startMin: number; endMin: number }[][] = [];
    for (const appt of sorted) {
        const { hour, minute } = parseTime(appt.appointment_time);
        const startMin = hour * 60 + minute;
        const endMin = startMin + (appt.duration_minutes || 30);

        let placed = false;
        for (const group of groups) {
            if (group.every(g => g.endMin <= startMin || g.startMin >= endMin)) {
                group.push({ appt, startMin, endMin });
                placed = true;
                break;
            }
        }
        if (!placed) {
            // Find a group that overlaps and add to it
            let foundGroup = false;
            for (const group of groups) {
                if (group.some(g => g.endMin > startMin && g.startMin < endMin)) {
                    group.push({ appt, startMin, endMin });
                    foundGroup = true;
                    break;
                }
            }
            if (!foundGroup) {
                groups.push([{ appt, startMin, endMin }]);
            }
        }
    }

    const positioned: { appt: Appointment; left: number; width: number }[] = [];
    for (const group of groups) {
        // Within each group, assign columns
        const cols: { appt: Appointment; startMin: number; endMin: number }[][] = [];
        for (const item of group) {
            let placed = false;
            for (const col of cols) {
                if (col[col.length - 1].endMin <= item.startMin) {
                    col.push(item);
                    placed = true;
                    break;
                }
            }
            if (!placed) cols.push([item]);
        }
        const colCount = cols.length;
        const colWidth = (100 - 4) / colCount; // 4% padding
        cols.forEach((col, ci) => {
            for (const item of col) {
                positioned.push({
                    appt: item.appt,
                    left: ci * colWidth + 2,
                    width: colWidth - 1,
                });
            }
        });
    }

    return positioned;
}

function endTime(start: string, duration: number): string {
    const { hour, minute } = parseTime(start);
    const total = hour * 60 + minute + duration;
    return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

/* ══════════════════════════════════════════════════════════════════
   Mini Calendar (sidebar)
   ══════════════════════════════════════════════════════════════════ */

function MiniCalendar({ baseDate, today, onSelectDate }: {
    baseDate: Date;
    today: Date;
    onSelectDate: (d: Date) => void;
}) {
    const [viewMonth, setViewMonth] = useState(() => ({ year: baseDate.getFullYear(), month: baseDate.getMonth() }));

    useEffect(() => {
        setViewMonth({ year: baseDate.getFullYear(), month: baseDate.getMonth() });
    }, [baseDate]);

    const monthName = new Date(viewMonth.year, viewMonth.month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const firstDay = new Date(viewMonth.year, viewMonth.month, 1).getDay();
    const daysInMonth = new Date(viewMonth.year, viewMonth.month + 1, 0).getDate();
    const prevDays = new Date(viewMonth.year, viewMonth.month, 0).getDate();

    // Build cells starting from Monday
    const startOffset = (firstDay + 6) % 7; // Monday = 0
    const cells: { day: number; inMonth: boolean; date: Date }[] = [];

    for (let i = startOffset - 1; i >= 0; i--) {
        const d = prevDays - i;
        cells.push({ day: d, inMonth: false, date: new Date(viewMonth.year, viewMonth.month - 1, d) });
    }
    for (let d = 1; d <= daysInMonth; d++) {
        cells.push({ day: d, inMonth: true, date: new Date(viewMonth.year, viewMonth.month, d) });
    }
    const remainder = cells.length % 7;
    if (remainder > 0) {
        for (let d = 1; d <= 7 - remainder; d++) {
            cells.push({ day: d, inMonth: false, date: new Date(viewMonth.year, viewMonth.month + 1, d) });
        }
    }

    const weekDays = getWeekDays(baseDate);
    const weekStartStr = fmt(weekDays[0]);
    const weekEndStr = fmt(weekDays[6]);

    const isInSelectedWeek = (d: Date) => {
        const s = fmt(d);
        return s >= weekStartStr && s <= weekEndStr;
    };

    return (
        <div>
            {/* Month header */}
            <div className="flex items-center justify-between mb-sm">
                <button className={`${btnGhost} p-0.5`} onClick={() => setViewMonth(m => m.month === 0 ? { year: m.year - 1, month: 11 } : { year: m.year, month: m.month - 1 })}>
                    <ChevronLeft size={14} />
                </button>
                <span className="text-[0.8rem] font-semibold tracking-tight">{monthName}</span>
                <button className={`${btnGhost} p-0.5`} onClick={() => setViewMonth(m => m.month === 11 ? { year: m.year + 1, month: 0 } : { year: m.year, month: m.month + 1 })}>
                    <ChevronRight size={14} />
                </button>
            </div>

            {/* Day labels */}
            <div className="grid grid-cols-7 mb-0.5">
                {['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].map(d => (
                    <div key={d} className="text-center text-[0.6rem] font-semibold uppercase text-text-tertiary py-0.5">{d}</div>
                ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7">
                {cells.map((cell, i) => {
                    const isToday = isSameDay(cell.date, today);
                    const inWeek = cell.inMonth && isInSelectedWeek(cell.date);

                    return (
                        <button
                            key={i}
                            className={`w-full aspect-square flex items-center justify-center text-[0.75rem] rounded-sm transition-all duration-100 ${!cell.inMonth ? 'text-text-tertiary/40' : 'text-text-secondary hover:bg-bg-tertiary cursor-pointer'} ${inWeek ? 'bg-accent-purple/10 text-accent-purple! font-semibold' : ''} ${isToday ? 'bg-accent-purple! text-white! font-bold rounded-full' : ''}`}
                            onClick={() => cell.inMonth && onSelectDate(cell.date)}
                        >
                            {cell.day}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Status Badge ──────────────────────────────────────────────── */

function StatusBadge({ status, label }: { status: string; label?: string }) {
    const colors: Record<string, string> = {
        active: 'bg-success/10 text-success before:bg-success',
        confirmed: 'bg-success/10 text-success before:bg-success',
        resolved: 'bg-success/10 text-success before:bg-success',
        cancelled: 'bg-error/10 text-error before:bg-error',
        completed: 'bg-accent-purple/10 text-accent-purple before:bg-accent-purple',
        escalated: 'bg-accent-orange/10 text-accent-orange before:bg-accent-orange',
        processing: 'bg-warning/10 text-warning before:bg-warning',
        pending: 'bg-warning/10 text-warning before:bg-warning',
        ready: 'bg-info/10 text-info before:bg-info',
    };
    const icon = status === 'confirmed' ? <Clock size={12} />
        : status === 'completed' ? <CheckCircle size={12} />
            : status === 'cancelled' ? <XCircle size={12} />
                : null;
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium tracking-wide before:content-[''] before:w-1.5 before:h-1.5 before:rounded-full ${colors[status] || 'bg-bg-tertiary text-text-secondary before:bg-text-tertiary'}`}>
            {icon} {label || status}
        </span>
    );
}

/* ── Create Appointment Modal ───────────────────────────────────── */

function CreateAppointmentModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void; }) {
    const [form, setForm] = useState({ customer_ig_id: '', customer_name: '', customer_surname: '', appointment_date: '', appointment_time: '', service_type: '', subject: '', notes: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await appointments.create(form as any);
            onCreated();
        } catch (err: any) {
            setError(err.message);
        }
        setLoading(false);
    };

    return (
        <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-[8px] flex items-center justify-center p-xl animate-fade-in" onClick={onClose}>
            <div className="bg-bg-elevated border border-border-default rounded-xl p-xl w-full max-w-[520px] max-h-[85vh] overflow-y-auto animate-slide-up" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-lg">
                    <h3 className="text-xl font-semibold tracking-tight">New Appointment</h3>
                    <button className={`${btnGhost} ${btnSm}`} onClick={onClose}><X size={18} /></button>
                </div>

                {error && <div className="bg-error/10 border border-error/20 rounded-md p-md mb-md text-error text-sm">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="grid grid-cols-3 gap-md">
                        <div className="mb-md">
                            <label className={labelClass}>Customer IG ID</label>
                            <input className={inputClass} required value={form.customer_ig_id} onChange={e => setForm(f => ({ ...f, customer_ig_id: e.target.value }))} />
                        </div>
                        <div className="mb-md">
                            <label className={labelClass}>Customer Name</label>
                            <input className={inputClass} value={form.customer_name} onChange={e => setForm(f => ({ ...f, customer_name: e.target.value }))} />
                        </div>
                        <div className="mb-md">
                            <label className={labelClass}>Customer Surname</label>
                            <input className={inputClass} value={form.customer_surname} onChange={e => setForm(f => ({ ...f, customer_surname: e.target.value }))} />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-md">
                        <div className="mb-md">
                            <label className={labelClass}>Date</label>
                            <input className={inputClass} type="date" required value={form.appointment_date} onChange={e => setForm(f => ({ ...f, appointment_date: e.target.value }))} />
                        </div>
                        <div className="mb-md">
                            <label className={labelClass}>Time</label>
                            <input className={inputClass} type="time" required value={form.appointment_time} onChange={e => setForm(f => ({ ...f, appointment_time: e.target.value }))} />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-md">
                        <div className="mb-md">
                            <label className={labelClass}>Subject</label>
                            <input className={inputClass} placeholder="e.g. Follow-up consultation" value={form.subject} onChange={e => setForm(f => ({ ...f, subject: e.target.value }))} />
                        </div>
                        <div className="mb-md">
                            <label className={labelClass}>Service Type</label>
                            <input className={inputClass} placeholder="e.g. Consultation" value={form.service_type} onChange={e => setForm(f => ({ ...f, service_type: e.target.value }))} />
                        </div>
                    </div>
                    <div className="mb-md">
                        <label className={labelClass}>Notes</label>
                        <textarea className={`${inputClass} min-h-[80px] resize-y`} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                    </div>
                    <div className="flex justify-end gap-sm mt-lg pt-md border-t border-border-subtle">
                        <button type="button" className={btnSecondary} onClick={onClose}>Cancel</button>
                        <button type="submit" className={btnPrimary} disabled={loading}>{loading ? 'Creating...' : 'Create'}</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
