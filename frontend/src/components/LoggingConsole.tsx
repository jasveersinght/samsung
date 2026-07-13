import React, { useState, useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  logger: string;
}

interface LoggingConsoleProps {
  logs: LogEntry[];
  topicLogs: string[];
}

export const LoggingConsole: React.FC<LoggingConsoleProps> = ({ logs, topicLogs }) => {
  const [activeTab, setActiveTab] = useState<'system' | 'ros'>('system');
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const rosEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logic when new logs are received
  useEffect(() => {
    if (activeTab === 'system') {
      consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    } else {
      rosEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, topicLogs, activeTab]);

  const getLogLevelClass = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400 font-bold';
      case 'WARNING':
        return 'text-amber-400';
      case 'DEBUG':
        return 'text-zinc-500';
      default:
        return 'text-zinc-300';
    }
  };

  return (
    <div className="flex flex-col h-full bg-panelBg border border-borderColor rounded-lg overflow-hidden">
      {/* Console Tab Selector Headers */}
      <div className="flex justify-between items-center bg-darkBg px-4 py-2 border-b border-borderColor">
        <div className="flex items-center gap-2 text-xs font-semibold text-textMain">
          <Terminal className="w-4 h-4 text-zinc-400" />
          <span>ROS 2 / Planner Log Console</span>
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={() => setActiveTab('system')}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors duration-150 ${
              activeTab === 'system'
                ? 'bg-zinc-800 text-textMain border border-zinc-700'
                : 'text-textMuted hover:text-textMain'
            }`}
          >
            System/Planner Logs
          </button>
          <button
            onClick={() => setActiveTab('ros')}
            className={`px-3 py-1 rounded text-xs font-mono transition-colors duration-150 ${
              activeTab === 'ros'
                ? 'bg-zinc-800 text-textMain border border-zinc-700'
                : 'text-textMuted hover:text-textMain'
            }`}
          >
            ROS 2 Topics
          </button>
        </div>
      </div>

      {/* Log Console Terminal Area */}
      <div className="flex-1 bg-darkBg/60 p-3 overflow-y-auto font-mono text-[11px] leading-relaxed">
        {activeTab === 'system' ? (
          <div className="space-y-1">
            {logs.length === 0 ? (
              <span className="text-zinc-600 italic">No system log logs recorded...</span>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="flex gap-2.5">
                  <span className="text-zinc-600 shrink-0">{log.timestamp}</span>
                  <span className={`shrink-0 w-12 text-right ${getLogLevelClass(log.level)}`}>
                    [{log.level}]
                  </span>
                  <span className="text-zinc-500 shrink-0 font-bold">[{log.logger.split('.').pop()}]:</span>
                  <span className={getLogLevelClass(log.level)}>{log.message}</span>
                </div>
              ))
            )}
            <div ref={consoleEndRef} />
          </div>
        ) : (
          <div className="space-y-1">
            {topicLogs.length === 0 ? (
              <span className="text-zinc-600 italic">No active ROS 2 node messages on `/odom` or `/cmd_vel`...</span>
            ) : (
              topicLogs.map((log, i) => {
                // Colorize topics based on string contents
                let colorClass = 'text-zinc-400';
                if (log.includes('/odom')) colorClass = 'text-sky-300';
                if (log.includes('/cmd_vel')) colorClass = 'text-teal-400';
                if (log.includes('/joint_states')) colorClass = 'text-purple-300';

                return (
                  <div key={i} className={`${colorClass} whitespace-pre-wrap`}>
                    {log}
                  </div>
                );
              })
            )}
            <div ref={rosEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};
export default LoggingConsole;
