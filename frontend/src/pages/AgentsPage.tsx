import { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bot, Plus, Upload, FileText, Trash2, Settings, Shield, Power, X, Save, Instagram, Unlink, AlertTriangle, ChevronDown, Cpu, Eye, EyeOff } from 'lucide-react';
import { agents, instagram, type Agent, type KnowledgeDocument, type InstagramAccount, type LlmProvider } from '../lib/api';

/* ── Shared class strings ──────────────────────────────────────── */

const inputClass = "w-full py-2.5 px-3.5 bg-bg-tertiary border border-border-default rounded-md text-text-primary text-sm transition-all duration-150 outline-none focus:border-accent-purple focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] placeholder:text-text-tertiary";
const labelClass = "block text-[0.8rem] font-medium text-text-secondary mb-xs uppercase tracking-wider";
const btnPrimary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange text-white shadow-sm hover:shadow-glow hover:-translate-y-px transition-all duration-150";
const btnSecondary = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-bg-tertiary border border-border-default text-text-primary hover:bg-bg-card-hover hover:border-border-strong transition-all duration-150";
const btnGhost = "inline-flex items-center justify-center gap-sm text-text-secondary hover:bg-bg-tertiary hover:text-text-primary transition-all duration-150";
const btnDanger = "inline-flex items-center justify-center gap-sm px-5 py-2.5 rounded-md text-sm font-medium bg-error/10 text-error border border-error/20 hover:bg-error/20 transition-all duration-150";
const btnSm = "px-3 py-1.5 text-[0.8rem]";
const cardClass = "bg-bg-card border border-border-subtle rounded-lg p-lg transition-all duration-250 hover:border-border-default hover:shadow-md";

export function AgentsPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [agentList, setAgentList] = useState<Agent[]>([]);
    const [igAccounts, setIgAccounts] = useState<InstagramAccount[]>([]);
    const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
    const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [toast, setToast] = useState<string | null>(null);
    const [unlinkTarget, setUnlinkTarget] = useState<InstagramAccount | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Agent | null>(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        loadData();

        const linked = searchParams.get('linked');
        const username = searchParams.get('username');
        const error = searchParams.get('error');
        if (linked === 'true') {
            setToast(`@${username || 'account'} connected successfully!`);
            setSearchParams({}, { replace: true });
            setTimeout(() => setToast(null), 5000);
        } else if (error === 'account_owned_by_another_user') {
            setToast('This Instagram account is already linked to another user');
            setSearchParams({}, { replace: true });
            setTimeout(() => setToast(null), 6000);
        } else if (error) {
            setToast(`Connection failed: ${error.replace(/_/g, ' ')}`);
            setSearchParams({}, { replace: true });
            setTimeout(() => setToast(null), 5000);
        }
    }, []);

    const loadData = async () => {
        try {
            const [agentsData, accountsData, providersData] = await Promise.all([
                agents.list().catch(() => []),
                instagram.listAccounts().catch(() => []),
                agents.listLlmProviders().catch(() => []),
            ]);
            setAgentList(agentsData);
            setIgAccounts(accountsData);
            setLlmProviders(providersData);
        } catch { /* empty */ }
        setLoading(false);
    };

    const selectAgent = async (agent: Agent) => {
        setSelectedAgent(agent);
        try {
            const d = await agents.listDocuments(agent.id);
            setDocs(d);
        } catch { setDocs([]); }
    };

    const handleConnectInstagram = async () => {
        try {
            const { auth_url } = await instagram.getAuthUrl();
            window.location.href = auth_url;
        } catch (err: any) {
            setToast(err.message || 'Failed to get auth URL');
            setTimeout(() => setToast(null), 4000);
        }
    };

    const handleUnlink = async () => {
        if (!unlinkTarget) return;
        try {
            await instagram.deleteAccount(unlinkTarget.id);
            setIgAccounts(prev => prev.filter(a => a.id !== unlinkTarget.id));
            if (selectedAgent && agentList.some(a => a.instagram_account_id === unlinkTarget.id && a.id === selectedAgent.id)) {
                setSelectedAgent(null);
            }
            setAgentList(prev => prev.filter(a => a.instagram_account_id !== unlinkTarget.id));
            setToast(`@${unlinkTarget.ig_username} disconnected`);
            setTimeout(() => setToast(null), 4000);
        } catch (err: any) {
            setToast(err.message || 'Failed to disconnect account');
            setTimeout(() => setToast(null), 4000);
        }
        setUnlinkTarget(null);
    };

    const handleDeleteAgent = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await agents.delete(deleteTarget.id);
            setAgentList(prev => prev.filter(a => a.id !== deleteTarget.id));
            if (selectedAgent?.id === deleteTarget.id) {
                setSelectedAgent(null);
                setDocs([]);
            }
            setToast(`"${deleteTarget.name}" deleted successfully`);
            setTimeout(() => setToast(null), 4000);
        } catch (err: any) {
            setToast(err.message || 'Failed to delete agent');
            setTimeout(() => setToast(null), 4000);
        }
        setDeleting(false);
        setDeleteTarget(null);
    };

    if (loading) return <div className="max-w-[1400px] mx-auto p-xl w-full"><p className="text-text-secondary">Loading agents...</p></div>;

    const hasIgAccount = igAccounts.length > 0;

    return (
        <div className="max-w-[1400px] mx-auto px-lg py-xl w-full">
            {/* Toast */}
            {toast && (
                <div className="fixed top-20 right-lg z-[300] flex items-center gap-md px-lg py-md bg-bg-elevated border border-success/30 rounded-lg shadow-lg animate-slide-in text-sm before:content-['✓'] before:w-6 before:h-6 before:rounded-full before:bg-success/15 before:text-success before:flex before:items-center before:justify-center before:text-xs before:font-bold before:shrink-0">
                    {toast}
                </div>
            )}

            {/* Unlink Confirmation Modal */}
            {unlinkTarget && (
                <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-[8px] flex items-center justify-center p-xl animate-fade-in" onClick={() => setUnlinkTarget(null)}>
                    <div className="bg-bg-elevated border border-border-default rounded-xl p-xl w-full max-w-[440px] animate-slide-up" onClick={e => e.stopPropagation()}>
                        <div className="flex flex-col items-center text-center py-lg">
                            <div className="w-14 h-14 rounded-full bg-error/10 flex items-center justify-center mb-md">
                                <AlertTriangle size={28} className="text-error" />
                            </div>
                            <h3 className="text-lg font-semibold mb-sm">Disconnect @{unlinkTarget.ig_username}?</h3>
                            <p className="text-text-secondary text-sm leading-relaxed max-w-[320px]">
                                This will permanently remove this Instagram account and <strong className="text-error">delete its agent</strong>, including all conversations, messages, appointments, and knowledge documents.
                            </p>
                        </div>
                        <div className="flex justify-center gap-md mt-lg pt-md border-t border-border-subtle">
                            <button className={btnSecondary} onClick={() => setUnlinkTarget(null)}>Cancel</button>
                            <button className={btnDanger} onClick={handleUnlink}>
                                <Unlink size={14} /> Disconnect
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Agent Confirmation Modal */}
            {deleteTarget && (
                <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-[8px] flex items-center justify-center p-xl animate-fade-in" onClick={() => !deleting && setDeleteTarget(null)}>
                    <div className="bg-bg-elevated border border-border-default rounded-xl p-xl w-full max-w-[440px] animate-slide-up" onClick={e => e.stopPropagation()}>
                        <div className="flex flex-col items-center text-center py-lg">
                            <div className="w-14 h-14 rounded-full bg-error/10 flex items-center justify-center mb-md">
                                <AlertTriangle size={28} className="text-error" />
                            </div>
                            <h3 className="text-lg font-semibold mb-sm">Delete "{deleteTarget.name}"?</h3>
                            <p className="text-text-secondary text-sm leading-relaxed max-w-[320px]">
                                This will permanently delete this agent, its <strong className="text-error">knowledge base</strong>, and all uploaded documents. Conversations and appointments will be kept but unlinked.
                            </p>
                        </div>
                        <div className="flex justify-center gap-md mt-lg pt-md border-t border-border-subtle">
                            <button className={btnSecondary} onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</button>
                            <button className={btnDanger} onClick={handleDeleteAgent} disabled={deleting}>
                                <Trash2 size={14} /> {deleting ? 'Deleting...' : 'Delete Agent'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Page Header */}
            <div className="flex items-center justify-between mb-xl">
                <div>
                    <h1 className="text-[1.75rem] font-bold tracking-tight">Agents</h1>
                    <p className="text-text-secondary text-sm mt-xs">Manage your Instagram chatbot agents</p>
                </div>
                <div className="flex items-center gap-sm">
                    {hasIgAccount && (
                        <button className={btnPrimary} onClick={() => setShowCreateModal(true)}>
                            <Plus size={16} /> Create Agent
                        </button>
                    )}
                    <InstagramDropdown
                        accounts={igAccounts}
                        onConnect={handleConnectInstagram}
                        onUnlink={setUnlinkTarget}
                    />
                </div>
            </div>

            {agentList.length === 0 ? (
                <div className={cardClass}>
                    <div className="flex flex-col items-center justify-center py-3xl px-xl text-center">
                        <div className="w-16 h-16 rounded-lg bg-bg-tertiary flex items-center justify-center mb-md text-text-tertiary"><Bot size={28} /></div>
                        <h3 className="text-lg font-semibold mb-xs">No agents yet</h3>
                        <p className="text-text-secondary text-sm max-w-[360px]">{hasIgAccount
                            ? 'Create your first agent to start automating your Instagram DMs'
                            : 'Connect your Instagram account above, then create your first agent'
                        }</p>
                        {hasIgAccount && (
                            <button className={`${btnPrimary} mt-md`} onClick={() => setShowCreateModal(true)}>
                                <Plus size={16} /> Create Agent
                            </button>
                        )}
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-[320px_1fr] gap-md min-h-[60vh]">
                    {/* Agent List */}
                    <div className="flex flex-col gap-sm">
                        {agentList.map(agent => (
                            <div
                                key={agent.id}
                                className={`${cardClass} cursor-pointer ${selectedAgent?.id === agent.id ? 'border-accent-purple! shadow-glow!' : ''}`}
                                onClick={() => selectAgent(agent)}
                            >
                                <div className="flex items-center gap-md">
                                    <div className="w-10 h-10 rounded-md bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center">
                                        <Bot size={20} color="white" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-base font-semibold tracking-tight">{agent.name}</div>
                                        <div className="text-[0.8rem] text-text-secondary flex items-center gap-sm mt-0.5">
                                            <span>{agent.is_active ? '🟢 Active' : '🔴 Inactive'}</span>
                                            {agent.instagram_username && (
                                                <span className="inline-flex items-center gap-[3px] text-text-tertiary text-xs">
                                                    <Instagram size={11} /> @{agent.instagram_username}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Agent Detail */}
                    {selectedAgent ? (
                        <AgentDetail
                            agent={selectedAgent}
                            docs={docs}
                            llmProviders={llmProviders}
                            onUpdate={(a) => { setSelectedAgent(a); setAgentList(prev => prev.map(x => x.id === a.id ? a : x)); }}
                            onDocsChange={setDocs}
                            onDelete={(a) => setDeleteTarget(a)}
                        />
                    ) : (
                        <div className={cardClass}>
                            <div className="flex flex-col items-center justify-center py-3xl px-xl text-center">
                                <div className="w-16 h-16 rounded-lg bg-bg-tertiary flex items-center justify-center mb-md text-text-tertiary"><Settings size={28} /></div>
                                <h3 className="text-lg font-semibold mb-xs">Select an agent</h3>
                                <p className="text-text-secondary text-sm max-w-[360px]">Choose an agent from the list to view and edit its configuration</p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {showCreateModal && (
                <CreateAgentModal
                    igAccounts={igAccounts}
                    existingAgents={agentList}
                    llmProviders={llmProviders}
                    onClose={() => setShowCreateModal(false)}
                    onCreated={(a) => { setAgentList(prev => [...prev, a]); setShowCreateModal(false); selectAgent(a); }}
                />
            )}
        </div>
    );
}

/* ── Agent Detail Panel ─────────────────────────────────────────── */

function AgentDetail({ agent, docs, llmProviders, onUpdate, onDocsChange, onDelete }: {
    agent: Agent;
    docs: KnowledgeDocument[];
    llmProviders: LlmProvider[];
    onUpdate: (a: Agent) => void;
    onDocsChange: (d: KnowledgeDocument[]) => void;
    onDelete: (a: Agent) => void;
}) {
    const [tab, setTab] = useState<'context' | 'permissions' | 'knowledge' | 'model'>('context');
    const [context, setContext] = useState(agent.system_context || '');
    const [saving, setSaving] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const [llmProvider, setLlmProvider] = useState(agent.llm_config?.provider || '');
    const [llmProviderConfig, setLlmProviderConfig] = useState<Record<string, string>>(agent.llm_config?.provider_config || {});
    const [llmTemp, setLlmTemp] = useState(agent.llm_config?.temperature ?? 0.3);
    const [llmMaxTokens, setLlmMaxTokens] = useState(agent.llm_config?.max_tokens ?? 2048);

    const selectedProviderDef = llmProviders.find(p => p.id === llmProvider);

    useEffect(() => {
        setContext(agent.system_context || '');
        setLlmProvider(agent.llm_config?.provider || '');
        setLlmProviderConfig(agent.llm_config?.provider_config || {});
        setLlmTemp(agent.llm_config?.temperature ?? 0.3);
        setLlmMaxTokens(agent.llm_config?.max_tokens ?? 2048);
    }, [agent.id]);

    // Reset provider config when provider changes
    const handleProviderChange = (newProvider: string) => {
        setLlmProvider(newProvider);
        // Populate defaults from provider definition
        const providerDef = llmProviders.find(p => p.id === newProvider);
        if (providerDef) {
            const defaults: Record<string, string> = {};
            providerDef.fields.forEach(f => {
                if (f.default) defaults[f.key] = f.default;
            });
            setLlmProviderConfig(defaults);
        } else {
            setLlmProviderConfig({});
        }
    };

    const saveContext = async () => {
        setSaving(true);
        try {
            const updated = await agents.update(agent.id, { system_context: context });
            onUpdate(updated);
        } catch { /* empty */ }
        setSaving(false);
    };

    const togglePermission = async (key: string) => {
        const newPerms = { ...agent.permissions, [key]: !agent.permissions[key] };
        try {
            const updated = await agents.updatePermissions(agent.id, newPerms);
            onUpdate(updated);
        } catch { /* empty */ }
    };

    const toggleActive = async () => {
        try {
            const updated = await agents.toggle(agent.id);
            onUpdate(updated);
        } catch { /* empty */ }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            const doc = await agents.uploadDocument(agent.id, file);
            onDocsChange([...docs, doc]);
        } catch { /* empty */ }
        if (fileRef.current) fileRef.current.value = '';
    };

    const handleDeleteDoc = async (docId: string) => {
        try {
            await agents.deleteDocument(agent.id, docId);
            onDocsChange(docs.filter(d => d.id !== docId));
        } catch { /* empty */ }
    };

    const permissionLabels: Record<string, string> = {
        read_messages: '📖 Read Messages',
        write_messages: '✍️ Write Messages',
        send_email: '📧 Send Email',
        manage_appointments: '📅 Manage Appointments',
    };

    const tabClass = (t: string) =>
        `relative flex items-center gap-sm px-lg py-md text-sm font-medium transition-all duration-150 ${tab === t
            ? 'text-text-primary after:absolute after:bottom-[-1px] after:left-md after:right-md after:h-0.5 after:bg-gradient-to-r after:from-accent-purple after:via-accent-pink after:to-accent-orange after:rounded-full'
            : 'text-text-secondary hover:text-text-primary'
        }`;

    return (
        <div className="bg-bg-card border border-border-subtle rounded-lg overflow-hidden animate-slide-up">
            {/* Header */}
            <div className="p-lg border-b border-border-subtle flex justify-between items-center">
                <div className="flex items-center gap-md">
                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-accent-purple via-accent-pink to-accent-orange flex items-center justify-center">
                        <Bot size={24} color="white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold">{agent.name}</h2>
                        <div className="flex items-center gap-sm mt-1">
                            <StatusBadge status={agent.is_active ? 'active' : 'cancelled'} label={agent.is_active ? 'Active' : 'Inactive'} />
                            {agent.instagram_username && (
                                <span className="inline-flex items-center gap-1 text-[0.8rem] text-text-secondary">
                                    <Instagram size={13} /> @{agent.instagram_username}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-sm">
                    <button className={`${agent.is_active ? btnDanger : btnPrimary} ${btnSm}`} onClick={toggleActive}>
                        <Power size={14} /> {agent.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button className={`${btnGhost} ${btnSm} text-error hover:bg-error/10`} onClick={() => onDelete(agent)} title="Delete agent">
                        <Trash2 size={14} />
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border-subtle px-lg">
                {(['context', 'model', 'permissions', 'knowledge'] as const).map(t => (
                    <button key={t} className={tabClass(t)} onClick={() => setTab(t)}>
                        {t === 'context' && <Settings size={14} />}
                        {t === 'model' && <Cpu size={14} />}
                        {t === 'permissions' && <Shield size={14} />}
                        {t === 'knowledge' && <FileText size={14} />}
                        <span className="capitalize">{t === 'knowledge' ? 'Knowledge Base' : t === 'model' ? 'LLM' : t}</span>
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="p-lg">
                {tab === 'context' && (
                    <div className="animate-slide-up">
                        <div className="mb-md">
                            <label className={labelClass}>System Context / Business Prompt</label>
                            <textarea
                                className={`${inputClass} min-h-[200px] resize-y leading-relaxed`}
                                value={context}
                                onChange={e => setContext(e.target.value)}
                                placeholder="Describe your business, services, policies, and how the agent should behave..."
                            />
                        </div>
                        <button className={btnPrimary} onClick={saveContext} disabled={saving}>
                            <Save size={14} /> {saving ? 'Saving...' : 'Save Context'}
                        </button>
                    </div>
                )}

                {tab === 'model' && (
                    <div className="animate-slide-up flex flex-col gap-md">
                        {/* Provider Selection */}
                        <div>
                            <label className={labelClass}>LLM Provider</label>
                            <div className="grid grid-cols-2 gap-sm mt-xs">
                                {llmProviders.map(p => (
                                    <button
                                        key={p.id}
                                        type="button"
                                        onClick={() => handleProviderChange(p.id)}
                                        className={`flex flex-col items-start gap-xs p-md rounded-lg border text-left transition-all duration-150 ${llmProvider === p.id
                                            ? 'border-accent-purple bg-accent-purple/5 shadow-[0_0_0_3px_rgba(139,92,246,0.1)]'
                                            : 'border-border-default bg-bg-tertiary hover:border-border-strong hover:bg-bg-card-hover'
                                            }`}
                                    >
                                        <div className="flex items-center gap-sm w-full">
                                            <Cpu size={16} className={llmProvider === p.id ? 'text-accent-purple' : 'text-text-tertiary'} />
                                            <span className="text-sm font-semibold">{p.name}</span>
                                            {llmProvider === p.id && (
                                                <span className="ml-auto w-2 h-2 rounded-full bg-accent-purple" />
                                            )}
                                        </div>
                                        <span className="text-[0.75rem] text-text-tertiary leading-snug">{p.description}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Dynamic Provider Config Fields */}
                        {selectedProviderDef && (
                            <div className="border border-border-subtle rounded-lg p-md mt-xs">
                                <h4 className="text-[0.8rem] font-semibold text-text-secondary uppercase tracking-wider mb-md">
                                    {selectedProviderDef.name} Configuration
                                </h4>
                                <div className="flex flex-col gap-md">
                                    {selectedProviderDef.fields.map(field => (
                                        <ProviderConfigField
                                            key={field.key}
                                            field={field}
                                            value={llmProviderConfig[field.key] || ''}
                                            onChange={(val) => setLlmProviderConfig(prev => ({ ...prev, [field.key]: val }))}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Temperature + Max Tokens */}
                        <div className="grid grid-cols-2 gap-md">
                            <div>
                                <label className={labelClass}>Temperature: {llmTemp.toFixed(1)}</label>
                                <input type="range" min="0" max="2" step="0.1" value={llmTemp} onChange={e => setLlmTemp(parseFloat(e.target.value))} className="form-range" />
                                <div className="flex justify-between text-[0.7rem] text-text-tertiary mt-0.5">
                                    <span>Precise</span><span>Creative</span>
                                </div>
                            </div>
                            <div>
                                <label className={labelClass}>Max Tokens</label>
                                <input className={inputClass} type="number" min={128} max={16384} value={llmMaxTokens} onChange={e => setLlmMaxTokens(parseInt(e.target.value) || 2048)} />
                            </div>
                        </div>

                        <button className={btnPrimary} disabled={saving} onClick={async () => {
                            setSaving(true);
                            try {
                                const updated = await agents.updateLlmConfig(agent.id, {
                                    provider: llmProvider || undefined,
                                    provider_config: Object.keys(llmProviderConfig).length ? llmProviderConfig : undefined,
                                    temperature: llmTemp,
                                    max_tokens: llmMaxTokens,
                                });
                                onUpdate(updated);
                            } catch { /* empty */ }
                            setSaving(false);
                        }}>
                            <Save size={14} /> {saving ? 'Saving...' : 'Save LLM Config'}
                        </button>
                    </div>
                )}

                {tab === 'permissions' && (
                    <div className="animate-slide-up flex flex-col gap-md">
                        {Object.entries(permissionLabels).map(([key, label]) => (
                            <div key={key} className="flex items-center justify-between p-md bg-bg-tertiary rounded-md">
                                <span className="text-[0.9rem]">{label}</span>
                                <div
                                    className={`toggle-switch ${agent.permissions[key] ? 'active' : ''}`}
                                    onClick={() => togglePermission(key)}
                                />
                            </div>
                        ))}
                    </div>
                )}

                {tab === 'knowledge' && (
                    <div className="animate-slide-up">
                        <div className="flex justify-between items-center mb-md">
                            <span className="text-sm text-text-secondary">{docs.length} document{docs.length !== 1 ? 's' : ''} uploaded</span>
                            <label className={`${btnSecondary} ${btnSm} cursor-pointer`}>
                                <Upload size={14} /> Upload PDF
                                <input ref={fileRef} type="file" accept=".pdf" onChange={handleUpload} className="hidden" />
                            </label>
                        </div>

                        {docs.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-xl text-center">
                                <div className="w-16 h-16 rounded-lg bg-bg-tertiary flex items-center justify-center mb-md text-text-tertiary"><FileText size={28} /></div>
                                <h3 className="text-lg font-semibold mb-xs">No documents</h3>
                                <p className="text-text-secondary text-sm max-w-[360px]">Upload PDFs about your business to train the agent's knowledge base</p>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-sm">
                                {docs.map(doc => (
                                    <div key={doc.id} className="flex items-center gap-md p-md bg-bg-tertiary rounded-md">
                                        <FileText size={18} className="text-accent-purple shrink-0" />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium overflow-hidden text-ellipsis whitespace-nowrap">{doc.filename}</div>
                                            <div className="text-xs text-text-tertiary flex gap-md">
                                                {doc.page_count && <span>{doc.page_count} pages</span>}
                                                {doc.chunk_count && <span>{doc.chunk_count} chunks</span>}
                                                {doc.file_size_bytes && <span>{(doc.file_size_bytes / 1024).toFixed(0)} KB</span>}
                                            </div>
                                        </div>
                                        <StatusBadge status={doc.status} />
                                        <button className={`${btnGhost} ${btnSm}`} onClick={() => handleDeleteDoc(doc.id)} title="Delete">
                                            <Trash2 size={14} className="text-error" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

/* ── Provider Config Field ─────────────────────────────────────── */

function ProviderConfigField({ field, value, onChange }: {
    field: { key: string; label: string; type: string; required: boolean; secret: boolean; placeholder: string; help_text: string; options: { value: string; label: string }[]; default: string };
    value: string;
    onChange: (val: string) => void;
}) {
    const [showSecret, setShowSecret] = useState(false);
    // Check if the value looks masked (contains •)
    const isMasked = value.includes('•');
    const [isEditing, setIsEditing] = useState(false);

    if (field.type === 'select' && field.options.length > 0) {
        return (
            <div>
                <label className={labelClass}>
                    {field.label}
                    {!field.required && <span className="text-text-tertiary font-normal ml-1">(optional)</span>}
                </label>
                <select className={`${inputClass} form-select`} value={value || field.default} onChange={e => onChange(e.target.value)}>
                    {!field.required && <option value="">—</option>}
                    {field.options.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
                {field.help_text && <p className="text-[0.7rem] text-text-tertiary mt-xs">{field.help_text}</p>}
            </div>
        );
    }

    if (field.secret) {
        return (
            <div>
                <label className={labelClass}>
                    {field.label}
                    {!field.required && <span className="text-text-tertiary font-normal ml-1">(optional)</span>}
                </label>
                {isMasked && !isEditing ? (
                    <div className="flex items-center gap-sm">
                        <div className={`${inputClass} flex-1 flex items-center text-text-tertiary font-mono tracking-wider`}>
                            {value}
                        </div>
                        <button
                            type="button"
                            className={`${btnSecondary} ${btnSm} shrink-0`}
                            onClick={() => { setIsEditing(true); onChange(''); }}
                        >
                            Change
                        </button>
                    </div>
                ) : (
                    <div className="relative">
                        <input
                            className={`${inputClass} pr-10`}
                            type={showSecret ? 'text' : 'password'}
                            value={value}
                            onChange={e => onChange(e.target.value)}
                            placeholder={field.placeholder}
                            required={field.required}
                        />
                        <button
                            type="button"
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-tertiary hover:text-text-primary transition-colors"
                            onClick={() => setShowSecret(!showSecret)}
                            tabIndex={-1}
                        >
                            {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                    </div>
                )}
                {field.help_text && <p className="text-[0.7rem] text-text-tertiary mt-xs">{field.help_text}</p>}
            </div>
        );
    }

    return (
        <div>
            <label className={labelClass}>
                {field.label}
                {!field.required && <span className="text-text-tertiary font-normal ml-1">(optional)</span>}
            </label>
            <input
                className={inputClass}
                value={value}
                onChange={e => onChange(e.target.value)}
                placeholder={field.placeholder}
                required={field.required}
            />
            {field.help_text && <p className="text-[0.7rem] text-text-tertiary mt-xs">{field.help_text}</p>}
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
        error: 'bg-error/10 text-error before:bg-error',
        completed: 'bg-accent-purple/10 text-accent-purple before:bg-accent-purple',
        escalated: 'bg-accent-orange/10 text-accent-orange before:bg-accent-orange',
        processing: 'bg-warning/10 text-warning before:bg-warning',
        pending: 'bg-warning/10 text-warning before:bg-warning',
        ready: 'bg-info/10 text-info before:bg-info',
    };
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium tracking-wide before:content-[''] before:w-1.5 before:h-1.5 before:rounded-full ${colors[status] || 'bg-bg-tertiary text-text-secondary before:bg-text-tertiary'}`}>
            {label || status}
        </span>
    );
}

/* ── Create Agent Modal ─────────────────────────────────────────── */

function CreateAgentModal({ igAccounts, existingAgents, llmProviders, onClose, onCreated }: {
    igAccounts: InstagramAccount[];
    existingAgents: Agent[];
    llmProviders: LlmProvider[];
    onClose: () => void;
    onCreated: (a: Agent) => void;
}) {
    const linkedAccountIds = new Set(existingAgents.map(a => a.instagram_account_id));
    const availableAccounts = igAccounts.filter(acc => !linkedAccountIds.has(acc.id));

    const [name, setName] = useState('');
    const [selectedAccountId, setSelectedAccountId] = useState(availableAccounts[0]?.id || '');
    const [llmProvider, setLlmProvider] = useState(llmProviders[0]?.id || '');
    const [providerConfig, setProviderConfig] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const selectedProviderDef = llmProviders.find(p => p.id === llmProvider);

    const handleProviderChange = (newProvider: string) => {
        setLlmProvider(newProvider);
        const providerDef = llmProviders.find(p => p.id === newProvider);
        if (providerDef) {
            const defaults: Record<string, string> = {};
            providerDef.fields.forEach(f => {
                if (f.default) defaults[f.key] = f.default;
            });
            setProviderConfig(defaults);
        } else {
            setProviderConfig({});
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (linkedAccountIds.has(selectedAccountId)) {
            setError('This account is already linked to an agent');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const agent = await agents.create({
                instagram_account_id: selectedAccountId,
                name,
                llm_provider: llmProvider || undefined,
                llm_provider_config: Object.keys(providerConfig).length ? providerConfig : undefined,
            });
            onCreated(agent);
        } catch (err: any) {
            setError(err.message || 'Failed to create agent');
        }
        setLoading(false);
    };

    const noAvailable = availableAccounts.length === 0;

    return (
        <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-[8px] flex items-center justify-center p-xl animate-fade-in" onClick={onClose}>
            <div className="bg-bg-elevated border border-border-default rounded-xl p-xl w-full max-w-[560px] max-h-[85vh] overflow-y-auto animate-slide-up" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-lg">
                    <h3 className="text-xl font-semibold tracking-tight">Create Agent</h3>
                    <button className={`${btnGhost} ${btnSm}`} onClick={onClose}><X size={18} /></button>
                </div>

                {error && (
                    <div className="bg-error/10 border border-error/20 rounded-md p-md mb-md text-error text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleCreate}>
                    <div className="mb-md">
                        <label className={labelClass}>Agent Name</label>
                        <input className={inputClass} placeholder="My Business Bot" value={name} onChange={e => setName(e.target.value)} required />
                    </div>

                    <div className="mb-md">
                        <label className={labelClass}>Instagram Account</label>
                        {igAccounts.length > 0 ? (
                            <>
                                <select className={`${inputClass} form-select`} value={selectedAccountId} onChange={e => setSelectedAccountId(e.target.value)} required>
                                    {igAccounts.map(acc => {
                                        const isLinked = linkedAccountIds.has(acc.id);
                                        return (
                                            <option key={acc.id} value={acc.id} disabled={isLinked}>
                                                @{acc.ig_username}{isLinked ? ' (already linked)' : ''}
                                            </option>
                                        );
                                    })}
                                </select>
                                {noAvailable && (
                                    <p className="text-xs text-text-tertiary mt-xs">
                                        All accounts are linked to agents. Connect a new account or remove an existing agent first.
                                    </p>
                                )}
                            </>
                        ) : (
                            <div className="p-md bg-bg-tertiary rounded-md text-sm text-text-tertiary">
                                No Instagram accounts linked. Connect one first.
                            </div>
                        )}
                    </div>

                    {/* LLM Provider Selection */}
                    <div className="mb-md">
                        <label className={labelClass}>LLM Provider</label>
                        <div className="grid grid-cols-2 gap-sm mt-xs">
                            {llmProviders.map(p => (
                                <button
                                    key={p.id}
                                    type="button"
                                    onClick={() => handleProviderChange(p.id)}
                                    className={`flex flex-col items-start gap-xs p-md rounded-lg border text-left transition-all duration-150 ${llmProvider === p.id
                                        ? 'border-accent-purple bg-accent-purple/5 shadow-[0_0_0_3px_rgba(139,92,246,0.1)]'
                                        : 'border-border-default bg-bg-tertiary hover:border-border-strong'
                                        }`}
                                >
                                    <div className="flex items-center gap-sm">
                                        <Cpu size={14} className={llmProvider === p.id ? 'text-accent-purple' : 'text-text-tertiary'} />
                                        <span className="text-sm font-semibold">{p.name}</span>
                                        {llmProvider === p.id && <span className="ml-auto w-2 h-2 rounded-full bg-accent-purple" />}
                                    </div>
                                    <span className="text-[0.75rem] text-text-tertiary">{p.description}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Dynamic Provider Config Fields */}
                    {selectedProviderDef && (
                        <div className="border border-border-subtle rounded-lg p-md mb-md">
                            <h4 className="text-[0.8rem] font-semibold text-text-secondary uppercase tracking-wider mb-md">
                                {selectedProviderDef.name} Configuration
                            </h4>
                            <div className="flex flex-col gap-md">
                                {selectedProviderDef.fields.map(field => (
                                    <ProviderConfigField
                                        key={field.key}
                                        field={field}
                                        value={providerConfig[field.key] || ''}
                                        onChange={(val) => setProviderConfig(prev => ({ ...prev, [field.key]: val }))}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-sm mt-lg pt-md border-t border-border-subtle">
                        <button type="button" className={btnSecondary} onClick={onClose}>Cancel</button>
                        <button type="submit" className={btnPrimary} disabled={loading || !selectedAccountId || noAvailable}>
                            {loading ? 'Creating...' : 'Create Agent'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/* ── Instagram Dropdown ─────────────────────────────────────────── */

function InstagramDropdown({ accounts, onConnect, onUnlink }: {
    accounts: InstagramAccount[];
    onConnect: () => void;
    onUnlink: (acc: InstagramAccount) => void;
}) {
    const [open, setOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!open) return;
        const handleClick = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const hasAccounts = accounts.length > 0;

    return (
        <div ref={dropdownRef} className="relative">
            <button
                className="relative flex items-center gap-1.5 py-2 px-3 bg-[rgba(131,58,180,0.08)] border border-[rgba(131,58,180,0.2)] rounded-md text-text-primary cursor-pointer transition-all duration-150 hover:bg-[rgba(131,58,180,0.15)] hover:border-[rgba(131,58,180,0.35)]"
                onClick={() => setOpen(prev => !prev)}
                title={hasAccounts ? `${accounts.length} account${accounts.length > 1 ? 's' : ''} connected` : 'Connect Instagram'}
            >
                <Instagram size={18} />
                {hasAccounts && <span className="absolute top-1.5 right-1.5 w-[7px] h-[7px] rounded-full bg-success shadow-[0_0_6px_rgba(34,197,94,0.5)]" />}
                <ChevronDown size={14} className={`opacity-60 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
            </button>

            {open && (
                <div className="absolute top-[calc(100%+8px)] right-0 w-[280px] bg-bg-secondary border border-border-default rounded-lg shadow-lg z-[200] overflow-hidden animate-slide-up">
                    <div className="flex items-center justify-between px-md py-sm border-b border-border-default">
                        <span className="text-[0.8rem] font-semibold tracking-tight">Instagram Accounts</span>
                        <button className={`${btnGhost} p-0.5`} onClick={() => setOpen(false)}><X size={14} /></button>
                    </div>

                    {hasAccounts ? (
                        <div className="p-xs max-h-[200px] overflow-y-auto">
                            {accounts.map(acc => (
                                <div key={acc.id} className="flex items-center gap-sm px-sm py-sm rounded-md transition-colors duration-150 hover:bg-bg-tertiary">
                                    <Instagram size={14} className="text-[#E1306C] shrink-0" />
                                    <span className="flex-1 text-[0.825rem] font-medium">@{acc.ig_username}</span>
                                    <button
                                        onClick={() => { onUnlink(acc); setOpen(false); }}
                                        className={`${btnGhost} p-0.5 text-text-tertiary hover:text-error`}
                                        title="Disconnect"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-md text-center">
                            <p className="text-[0.8rem] text-text-tertiary mb-md">No accounts connected</p>
                        </div>
                    )}

                    <div className="px-md py-sm border-t border-border-default">
                        <button className="flex items-center justify-center gap-1.5 w-full py-2 bg-gradient-to-br from-[#833ab4] via-[#fd1d1d] to-[#fcb045] text-white rounded-md font-semibold text-[0.8rem] cursor-pointer transition-all duration-150 hover:opacity-90 hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(131,58,180,0.3)]" onClick={() => { onConnect(); setOpen(false); }}>
                            <Plus size={14} />
                            {hasAccounts ? 'Add Account' : 'Connect Instagram'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
