import { useEffect, useState } from 'react';
import { MessageSquare, ArrowLeft, Wrench } from 'lucide-react';
import { conversations, type Conversation, type ConversationDetail } from '../lib/api';

/* ── Shared class strings ──────────────────────────────────────── */

const btnPrimary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange text-white shadow-sm hover:shadow-glow hover:-translate-y-px transition-all duration-150";
const btnSecondary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-bg-tertiary border border-border-default text-text-primary hover:bg-bg-card-hover hover:border-border-strong transition-all duration-150";
const btnGhost = "inline-flex items-center justify-center gap-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-all duration-150";
const btnDanger = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-error/10 text-error border border-error/20 hover:bg-error/20 transition-all duration-150";
const btnSm = "px-3 py-1.5 text-[0.8rem]";

export function ChatHistoryPage() {
    const [list, setList] = useState<Conversation[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDetail, setSelectedDetail] = useState<ConversationDetail | null>(null);
    const [statusFilter, setStatusFilter] = useState('');

    useEffect(() => { loadConversations(); }, [statusFilter]);

    const loadConversations = async () => {
        setLoading(true);
        try {
            const params: Record<string, string> = {};
            if (statusFilter) params.status = statusFilter;
            const data = await conversations.list(params);
            setList(data);
        } catch { /* empty */ }
        setLoading(false);
    };

    const viewConversation = async (conv: Conversation) => {
        try {
            const detail = await conversations.get(conv.id);
            setSelectedDetail(detail);
        } catch { /* empty */ }
    };

    const updateStatus = async (id: string, status: string) => {
        try {
            await conversations.updateStatus(id, status);
            loadConversations();
            if (selectedDetail?.conversation.id === id) {
                setSelectedDetail(prev => prev ? { ...prev, conversation: { ...prev.conversation, status } } : null);
            }
        } catch { /* empty */ }
    };

    const formatTime = (iso: string) => {
        const d = new Date(iso);
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // Detail view
    if (selectedDetail) {
        return (
            <div className="max-w-[1400px] mx-auto px-lg py-xl w-full">
                <div className="mb-lg">
                    <button className={btnGhost} onClick={() => setSelectedDetail(null)}>
                        <ArrowLeft size={16} /> Back to conversations
                    </button>
                </div>

                <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden">
                    {/* Conv header */}
                    <div className="p-lg border-b border-border-subtle flex justify-between items-center">
                        <div>
                            <h2 className="text-lg font-semibold">
                                {selectedDetail.conversation.customer_username || selectedDetail.conversation.customer_ig_id}
                            </h2>
                            <div className="flex items-center gap-md mt-1">
                                <StatusBadge status={selectedDetail.conversation.status} />
                                <span className="text-xs text-text-tertiary">{selectedDetail.conversation.message_count} messages</span>
                            </div>
                        </div>
                        <div className="flex gap-sm">
                            {selectedDetail.conversation.status === 'active' && (
                                <>
                                    <button className={`${btnSecondary} ${btnSm}`} onClick={() => updateStatus(selectedDetail.conversation.id, 'resolved')}>
                                        ✅ Resolve
                                    </button>
                                    <button className={`${btnDanger} ${btnSm}`} onClick={() => updateStatus(selectedDetail.conversation.id, 'escalated')}>
                                        ⚠️ Escalate
                                    </button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex flex-col gap-md p-lg max-h-[60vh] overflow-y-auto">
                        {selectedDetail.messages.map(msg => (
                            <div key={msg.id} className={`max-w-[70%] p-md rounded-lg text-sm leading-relaxed ${msg.sender_type === 'customer'
                                ? 'self-start bg-bg-tertiary rounded-bl-sm'
                                : 'self-end bg-accent-purple/15 border border-accent-purple/20 rounded-br-sm'
                                }`}>
                                {msg.content}
                                <div className="flex items-center gap-sm mt-sm text-[0.7rem] text-text-tertiary">
                                    <span>{msg.sender_type === 'customer' ? '👤 Customer' : '🤖 Agent'}</span>
                                    <span>•</span>
                                    <span>{new Date(msg.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
                                </div>
                                {msg.tool_calls && Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0 && (
                                    <div className="flex gap-1 flex-wrap mt-1.5">
                                        {msg.tool_calls.map((tc: any, i: number) => (
                                            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-purple/10 text-accent-purple text-[0.7rem]">
                                                <Wrench size={10} /> {tc.tool}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // List view
    return (
        <div className="max-w-[1400px] mx-auto px-lg py-xl w-full">
            <div className="flex items-center justify-between mb-xl">
                <div>
                    <h1 className="text-[1.75rem] font-bold tracking-tight">Chat History</h1>
                    <p className="text-text-secondary text-sm mt-xs">View conversations between agents and customers</p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex gap-sm mb-md">
                {['', 'active', 'resolved', 'escalated'].map(f => (
                    <button
                        key={f}
                        className={`${btnSm} ${statusFilter === f ? btnPrimary : btnSecondary}`}
                        onClick={() => setStatusFilter(f)}
                    >
                        {f || 'All'}
                    </button>
                ))}
            </div>

            {/* Table */}
            <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden">
                {loading ? (
                    <div className="p-xl text-center text-text-secondary">Loading...</div>
                ) : list.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-3xl px-xl text-center">
                        <div className="w-16 h-16 rounded-lg bg-bg-tertiary flex items-center justify-center mb-md text-text-tertiary"><MessageSquare size={28} /></div>
                        <h3 className="text-lg font-semibold mb-xs">No conversations</h3>
                        <p className="text-text-secondary text-sm max-w-[360px]">When customers message your Instagram, conversations will appear here</p>
                    </div>
                ) : (
                    <table className="w-full border-collapse">
                        <thead>
                            <tr>
                                {['Customer', 'Messages', 'Last Message', 'Status', 'Started'].map(h => (
                                    <th key={h} className="px-md py-sm text-left text-xs font-semibold text-text-tertiary uppercase tracking-wider border-b border-border-subtle">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {list.map(conv => (
                                <tr key={conv.id} onClick={() => viewConversation(conv)} className="cursor-pointer animate-slide-up transition-colors duration-150 hover:bg-bg-card-hover">
                                    <td className="p-md text-sm border-b border-border-subtle align-middle">
                                        <div className="flex items-center gap-sm">
                                            <div className="w-8 h-8 rounded-full bg-bg-tertiary flex items-center justify-center text-[0.8rem] shrink-0">👤</div>
                                            <div>
                                                <div className="font-medium">{conv.customer_username || conv.customer_ig_id}</div>
                                                {conv.customer_username && <div className="text-xs text-text-tertiary">{conv.customer_ig_id}</div>}
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-md text-sm border-b border-border-subtle align-middle">
                                        <span className="font-semibold text-accent-purple">{conv.message_count}</span>
                                    </td>
                                    <td className="p-md text-sm border-b border-border-subtle align-middle text-text-secondary">{formatTime(conv.last_message_at)}</td>
                                    <td className="p-md text-sm border-b border-border-subtle align-middle">
                                        <StatusBadge status={conv.status} />
                                    </td>
                                    <td className="p-md text-[0.8rem] border-b border-border-subtle align-middle text-text-tertiary">
                                        {new Date(conv.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

/* ── Status Badge ──────────────────────────────────────────────── */

function StatusBadge({ status }: { status: string }) {
    const colors: Record<string, string> = {
        active: 'bg-success/10 text-success before:bg-success',
        confirmed: 'bg-success/10 text-success before:bg-success',
        resolved: 'bg-success/10 text-success before:bg-success',
        cancelled: 'bg-error/10 text-error before:bg-error',
        completed: 'bg-accent-purple/10 text-accent-purple before:bg-accent-purple',
        escalated: 'bg-accent-orange/10 text-accent-orange before:bg-accent-orange',
        processing: 'bg-warning/10 text-warning before:bg-warning',
        pending: 'bg-warning/10 text-warning before:bg-warning',
    };
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium tracking-wide before:content-[''] before:w-1.5 before:h-1.5 before:rounded-full ${colors[status] || 'bg-bg-tertiary text-text-secondary before:bg-text-tertiary'}`}>
            {status}
        </span>
    );
}
