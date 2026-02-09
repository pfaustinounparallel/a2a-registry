import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

const API_BASE = 'http://localhost:8000'; // point to registry

const AgentOperation = ({ operation, onClose }) => {
    const [agentJson, setAgentJson] = useState(`{
    "protocolVersion": "0.3.0",
    "name": "Example Agent",
    "description": "A test agent",
    "url": "http://example.com",
    "version": "1.0.0",
    "author": "Your Name",
    "capabilities": {"streaming": true},
    "skills": [{"id": "skill1", "name": "Example Skill", "tags": ["example"]}]
}`);
    const [result, setResult] = useState('');
    const [loading, setLoading] = useState(false);

    const handleAction = async (action) => {
        let payload;
        try {
            if (action !== 'delete') payload = JSON.parse(agentJson);
        } catch (err) {
            setResult(`JSON Parse Error: ${err.message}`);
            return;
        }

        let url = '';
        let method = '';

        if (action === 'validate') {
            url = `${API_BASE}/agents/validate`;
            method = 'POST';
        } else if (action === 'register') {
            url = `${API_BASE}/agents/register`;
            method = 'POST';
        } else if (action === 'delete') {
            try {
                const parsed = JSON.parse(agentJson);
                const agentId = parsed.name.toLowerCase().replace(/\s+/g, '-');
                url = `${API_BASE}/agents/${agentId}`;
                method = 'DELETE';
            } catch (err) {
                setResult(`JSON Parse Error: ${err.message}`);
                return;
            }
        }

        setLoading(true);
        setResult('');

        try {
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: method !== 'DELETE' ? JSON.stringify(payload) : undefined
            });

            if (!res.ok) {
                const errText = await res.text();
                setResult(`Error ${res.status}: ${errText}`);
                setLoading(false);
                return;
            }

            const data = await res.json().catch(() => ({}));
            setResult(JSON.stringify(data, null, 2));
        } catch (err) {
            setResult(`Fetch Error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-4 space-y-4 flex flex-col h-full">
            <div className="flex justify-between items-center">
                <h2 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-widest">Agent Operations</h2>
                <button onClick={onClose} className="text-zinc-400 hover:text-zinc-200">X</button>
            </div>
            <textarea
                className="w-full h-40 p-2 font-mono text-xs bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-sm"
                value={agentJson}
                onChange={(e) => setAgentJson(e.target.value)}
            />

            <div className="flex gap-2">
                {operation === 'validate' && (
                    <Button onClick={() => handleAction('validate')} disabled={loading}>
                        Validate
                    </Button>
                )}
                {operation === 'register' && (
                    <Button onClick={() => handleAction('register')} disabled={loading}>
                        Register
                    </Button>
                )}
                {operation === 'delete' && (
                    <Button variant="destructive" onClick={() => handleAction('delete')} disabled={loading}>
                        Delete
                    </Button>
                )}
            </div>

            <pre className="bg-zinc-950 p-3 border border-zinc-800 font-mono text-xs text-emerald-400 overflow-x-auto custom-scrollbar">
                {loading ? 'Processing...' : result}
            </pre>
        </div>
    );
};

export default AgentOperation;