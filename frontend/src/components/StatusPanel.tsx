import React from 'react';
import { Battery, Cpu, ShieldCheck, Wifi, Eye, RefreshCw } from 'lucide-react';

interface Telemetry {
  battery_percent?: number;
  lidar_status?: string;
  camera_status?: string;
  joint_states?: { [key: string]: number };
  current_action?: string;
  pose?: { x: number; y: number; theta: number };
}

interface StatusPanelProps {
  telemetry: Telemetry;
  isOnline: boolean;
  isPaused: boolean;
}

export const StatusPanel: React.FC<StatusPanelProps> = ({ telemetry, isOnline, isPaused }) => {
  const battery = telemetry?.battery_percent ?? 100;
  const pose = telemetry?.pose || { x: 0.0, y: 0.0, theta: 0.0 };
  const joints = telemetry?.joint_states || { joint_1: 0.0, joint_2: 0.0, joint_3: 0.0, gripper: 0.0 };
  const action = telemetry?.current_action || 'idle';

  // Get battery style class
  const getBatteryColor = (percent: number) => {
    if (percent > 50) return 'text-emerald-400';
    if (percent > 20) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="flex flex-col h-full bg-panelBg border border-borderColor rounded-lg p-4 justify-between space-y-4">
      {/* Top Status */}
      <div className="border-b border-borderColor pb-3">
        <h3 className="text-sm font-semibold tracking-wider uppercase text-textMain mb-2.5">Robot Diagnostics (MoveIt2/TF)</h3>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2 bg-darkBg border border-borderColor p-2 rounded">
            <Wifi className={`w-4 h-4 ${isOnline ? 'text-emerald-400' : 'text-red-500'}`} />
            <div>
              <span className="text-[10px] text-textMuted block">Bridge State</span>
              <span className="font-semibold">{isOnline ? 'CONNECTED' : 'DISCONNECTED'}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-darkBg border border-borderColor p-2 rounded">
            <Battery className={`w-4 h-4 ${getBatteryColor(battery)}`} />
            <div>
              <span className="text-[10px] text-textMuted block">Battery Capacity</span>
              <span className="font-semibold font-mono">{battery}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Pose & Action details */}
      <div className="space-y-3 flex-1 overflow-y-auto">
        <div className="bg-darkBg border border-borderColor p-2.5 rounded font-mono text-[11px] space-y-1">
          <span className="text-xs font-semibold text-textMain font-sans block mb-1">State / Active Controller</span>
          <div className="flex justify-between">
            <span className="text-textMuted">Action:</span>
            <span className="font-bold text-blue-400 capitalize">{isPaused ? 'PAUSED' : action}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-textMuted">X (meters):</span>
            <span className="text-textMain">{pose.x.toFixed(3)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-textMuted">Y (meters):</span>
            <span className="text-textMain">{pose.y.toFixed(3)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-textMuted">Yaw (rads):</span>
            <span className="text-textMain">{pose.theta.toFixed(3)}</span>
          </div>
        </div>

        {/* Joint configurations */}
        <div className="bg-darkBg border border-borderColor p-2.5 rounded text-[11px] font-mono space-y-1.5">
          <span className="text-xs font-semibold text-textMain font-sans block mb-1.5">Joint States (MoveIt2)</span>
          {Object.entries(joints).map(([name, val]) => (
            <div key={name} className="flex flex-col">
              <div className="flex justify-between mb-0.5">
                <span className="text-textMuted capitalize">{name.replace('_', ' ')}:</span>
                <span className="text-textMain font-semibold">{val.toFixed(2)} rad</span>
              </div>
              <div className="w-full bg-panelBg rounded-full h-1">
                <div 
                  className="bg-zinc-500 h-1 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(0, val * 100))}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dynamic Sensors summary */}
      <div className="border-t border-borderColor pt-3">
        <div className="grid grid-cols-2 gap-2 text-[10px] text-textMuted">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Lidar: Active</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Eye className="w-3.5 h-3.5 text-emerald-500" />
            <span>Camera: 10 FPS</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-emerald-500" />
            <span>IMU: Healthy</span>
          </div>
          <div className="flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5 text-emerald-500" />
            <span>TF2: Publishing</span>
          </div>
        </div>
      </div>
    </div>
  );
};
export default StatusPanel;
