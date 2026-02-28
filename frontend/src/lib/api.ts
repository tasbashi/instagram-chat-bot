const API_BASE = import.meta.env.VITE_API_URL || '';

function getToken(): string | null {
    return localStorage.getItem('token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }

    if (res.status === 204) return {} as T;
    return res.json();
}

// Upload with FormData (no JSON content-type)
async function uploadFile<T>(path: string, file: File): Promise<T> {
    const token = getToken();
    const form = new FormData();
    form.append('file', file);

    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers,
        body: form,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Upload failed');
    }

    return res.json();
}

// ── Auth ──

export const auth = {
    register: (data: { email: string; password: string; full_name?: string }) =>
        request<{ access_token: string }>('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    login: (data: { email: string; password: string }) =>
        request<{ access_token: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    me: () => request<User>('/api/auth/me'),
};

// ── Agents ──

export const agents = {
    list: () => request<Agent[]>('/api/agents'),
    get: (id: string) => request<Agent>(`/api/agents/${id}`),
    create: (data: {
        instagram_account_id: string;
        name: string;
        system_context?: string;
        llm_provider?: string;
        llm_provider_config?: Record<string, string>;
        temperature?: number;
        max_tokens?: number;
    }) =>
        request<Agent>('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name?: string; system_context?: string }) =>
        request<Agent>(`/api/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    updatePermissions: (id: string, data: Record<string, boolean>) =>
        request<Agent>(`/api/agents/${id}/permissions`, { method: 'PUT', body: JSON.stringify(data) }),
    toggle: (id: string) =>
        request<Agent>(`/api/agents/${id}/toggle`, { method: 'PUT' }),
    updateLlmConfig: (id: string, data: {
        provider?: string;
        provider_config?: Record<string, string>;
        temperature?: number;
        max_tokens?: number;
    }) =>
        request<Agent>(`/api/agents/${id}/llm-config`, { method: 'PUT', body: JSON.stringify(data) }),
    uploadDocument: (id: string, file: File) =>
        uploadFile<KnowledgeDocument>(`/api/agents/${id}/documents`, file),
    listDocuments: (id: string) =>
        request<KnowledgeDocument[]>(`/api/agents/${id}/documents`),
    deleteDocument: (agentId: string, docId: string) =>
        request<void>(`/api/agents/${agentId}/documents/${docId}`, { method: 'DELETE' }),
    listLlmProviders: () =>
        request<LlmProvider[]>('/api/agents/llm-providers'),
};

// ── Appointments ──

export const appointments = {
    list: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<Appointment[]>(`/api/appointments${qs}`);
    },
    create: (data: Partial<Appointment>) =>
        request<Appointment>('/api/appointments', { method: 'POST', body: JSON.stringify(data) }),
    cancel: (id: string, reason?: string) =>
        request<Appointment>(`/api/appointments/${id}/cancel`, { method: 'PUT', body: JSON.stringify({ cancellation_reason: reason }) }),
    complete: (id: string) =>
        request<Appointment>(`/api/appointments/${id}/complete`, { method: 'PUT' }),
};

// ── Conversations ──

export const conversations = {
    list: (params?: Record<string, string>) => {
        const qs = params ? '?' + new URLSearchParams(params).toString() : '';
        return request<Conversation[]>(`/api/conversations${qs}`);
    },
    get: (id: string) => request<ConversationDetail>(`/api/conversations/${id}`),
    updateStatus: (id: string, status: string) =>
        request<Conversation>(`/api/conversations/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),
};

// ── Instagram ──

export const instagram = {
    getAuthUrl: () => request<{ auth_url: string }>('/api/instagram/auth-url'),
    listAccounts: () => request<InstagramAccount[]>('/api/instagram/accounts'),
    deleteAccount: (id: string) => request<void>(`/api/instagram/accounts/${id}`, { method: 'DELETE' }),
};

// ── Types ──

export interface User {
    id: string;
    email: string;
    full_name: string | null;
    created_at: string;
}

export interface Agent {
    id: string;
    instagram_account_id: string;
    instagram_username: string | null;
    name: string;
    system_context: string | null;
    permissions: Record<string, boolean>;
    llm_config: {
        provider?: string;
        provider_config?: Record<string, string>;
        temperature?: number;
        max_tokens?: number;
    };
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface LlmProviderField {
    key: string;
    label: string;
    type: string;
    required: boolean;
    secret: boolean;
    placeholder: string;
    help_text: string;
    options: { value: string; label: string }[];
    default: string;
}

export interface LlmProvider {
    id: string;
    name: string;
    description: string;
    fields: LlmProviderField[];
}

export interface InstagramAccount {
    id: string;
    ig_user_id: string;
    ig_username: string;
    is_active: boolean;
    created_at: string | null;
}

export interface KnowledgeDocument {
    id: string;
    agent_id: string;
    filename: string;
    file_size_bytes: number | null;
    page_count: number | null;
    chunk_count: number | null;
    status: string;
    error_message: string | null;
    created_at: string;
}

export interface Appointment {
    id: string;
    agent_id: string | null;
    customer_ig_id: string;
    customer_name: string | null;
    customer_surname: string | null;
    appointment_date: string;
    appointment_time: string;
    duration_minutes: number;
    service_type: string | null;
    subject: string | null;
    notes: string | null;
    status: string;
    created_via: string;
    cancelled_at: string | null;
    cancellation_reason: string | null;
    created_at: string;
    updated_at: string;
}

export interface Conversation {
    id: string;
    agent_id: string | null;
    customer_ig_id: string;
    customer_username: string | null;
    status: string;
    started_at: string;
    last_message_at: string;
    message_count: number;
    resolved_at: string | null;
}

export interface Message {
    id: string;
    sender_type: string;
    content: string;
    tool_calls: Record<string, unknown>[] | null;
    rag_context: Record<string, unknown>[] | null;
    created_at: string;
}

export interface ConversationDetail {
    conversation: Conversation;
    messages: Message[];
}
