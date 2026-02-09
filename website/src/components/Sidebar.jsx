import React from 'react';
import { Filter, Cpu, Database, Network } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const Sidebar = ({
    allTags,
    selectedSkills,
    toggleSkillFilter,
    isMobile,
    setActiveOperation
}) => {
    return (
        <aside className={`${isMobile ? 'w-full border-none' : 'w-64 border-r'} border-zinc-800 bg-zinc-950 flex flex-col h-full shrink-0`}>
            {/* Section Header */}
            <div className="h-10 border-b border-zinc-800 flex items-center px-4 bg-zinc-900/30">
                <Filter className="w-3 h-3 text-emerald-500 mr-2" />
                <span className="text-xs font-mono font-bold text-zinc-400 tracking-wider">SEARCH FILTERS</span>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-4 space-y-6">
                    {/* Skill Cloud */}
                    <div className="space-y-3">
                        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Skill Tags</div>
                        <div className="flex flex-wrap gap-1.5">
                            {allTags.slice(0, 15).map(tag => (
                                <Badge
                                    key={tag}
                                    variant="outline"
                                    className={`
                                        cursor-pointer text-[10px] font-mono rounded-none border transition-all
                                        ${selectedSkills.includes(tag)
                                            ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-400'
                                            : 'bg-zinc-900/50 border-zinc-800 text-zinc-500 hover:border-zinc-600'
                                        }
                                    `}
                                    onClick={() => toggleSkillFilter(tag)}
                                >
                                    {tag}
                                </Badge>
                            ))}
                        </div>
                    </div>
                    {/* Agent Operations */}
                    <div className="space-y-2">
                        {/* Header */}
                        <div className="h-10 border-b border-zinc-800 flex items-center px-4 bg-zinc-900/30">
                            <Filter className="w-3 h-3 text-emerald-500 mr-2" />
                            <span className="text-xs font-mono font-bold text-zinc-400 tracking-wider">AGENT OPERATIONS</span>
                        </div>

                        {/* Buttons */}
                        <div className="flex flex-col gap-2 mt-2 px-4">
                            <button
                                className="w-full px-2 py-1 text-xs font-mono border border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400 transition-all"
                                onClick={() => setActiveOperation('validate')}
                            >
                                Validate Agent
                            </button>
                            <button
                                className="w-full px-2 py-1 text-xs font-mono border border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400 transition-all"
                                onClick={() => setActiveOperation('register')}
                            >
                                Register Agent
                            </button>
                            <button
                                className="w-full px-2 py-1 text-xs font-mono border border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400 transition-all"
                                onClick={() => setActiveOperation('delete')}
                            >
                                Delete Agent
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
