import React from 'react';

interface Telemetry {
  pose?: { x: number; y: number; theta: number };
  battery_percent?: number;
  current_action?: string;
}

interface RobotVisualizerProps {
  telemetry: Telemetry;
  plan: any;
}

export const RobotVisualizer: React.FC<RobotVisualizerProps> = ({ telemetry, plan }) => {
  const robotPose = telemetry?.pose || { x: 0, y: 0, theta: 0 };

  // SVG Dimension mappings
  const width = 450;
  const height = 350;

  // Scaling factors: maps robot space (x in [-5, 5], y in [-3, 8]) to SVG canvas (x in [0, 450], y in [0, 350])
  const scaleX = (rx: number) => {
    const minRx = -5, maxRx = 5;
    return ((rx - minRx) / (maxRx - minRx)) * width;
  };

  const scaleY = (ry: number) => {
    const minRy = -2, maxRy = 8;
    // Invert Y axis because SVG (0,0) is top-left
    return height - ((ry - minRy) / (maxRy - minRy)) * height;
  };

  // Pre-defined static room layouts
  const rooms = [
    { name: 'Office', x1: -4.5, y1: 0.5, x2: -1.5, y2: 3.5, color: 'rgba(63, 63, 70, 0.2)' },
    { name: 'Living Room', x1: -2, y1: -1.5, x2: 1, y2: 1.5, color: 'rgba(63, 63, 70, 0.1)' },
    { name: 'Kitchen', x1: 1, y1: 2.5, x2: 4.5, y2: 7.5, color: 'rgba(63, 63, 70, 0.2)' }
  ];

  // Specific spatial landmarks
  const landmarks = [
    { name: 'User', x: -1.0, y: -1.0, color: '#f43f5e' }, // Rose 500
    { name: 'Cupboard', x: 2.5, y: 6.0, color: '#3b82f6' }, // Blue 500
    { name: 'Sink', x: 1.5, y: 6.2, color: '#06b6d4' }, // Cyan 500
    { name: 'Dining Table', x: 3.0, y: 4.0, color: '#eab308' }, // Yellow 500
    { name: 'Countertop', x: 1.8, y: 4.8, color: '#a855f7' } // Purple 500
  ];

  // Objects layout
  const objects = [
    { name: 'Red Bottle', x: -3.0, y: 2.5, color: '#ef4444' },
    { name: 'Glass', x: 1.5, y: 6.2, color: '#10b981' }
  ];

  // Determine target navigation coordinate
  let targetCoords: { x: number; y: number } | null = null;
  if (plan && plan.tasks) {
    const activeTask = plan.tasks.find((t: any) => t.status === 'RUNNING');
    if (activeTask && activeTask.action === 'Navigate') {
      const dest = activeTask.parameters.destination;
      if (dest === 'kitchen') targetCoords = { x: 2.0, y: 5.0 };
      else if (dest === 'office') targetCoords = { x: -3.0, y: 2.0 };
      else if (dest === 'user') targetCoords = { x: -1.0, y: -1.0 };
      else if (dest === 'origin') targetCoords = { x: 0.0, y: 0.0 };
      else if (dest === 'cupboard') targetCoords = { x: 2.5, y: 6.0 };
      else if (dest === 'sink') targetCoords = { x: 1.5, y: 6.2 };
      else if (dest === 'dining table') targetCoords = { x: 3.0, y: 4.0 };
    }
  }

  return (
    <div className="flex flex-col h-full bg-panelBg border border-borderColor rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold tracking-wider uppercase text-textMain">Spatial Localization (TF2 Map)</h3>
        <span className="text-xs text-textMuted bg-darkBg px-2 py-0.5 rounded">Odom: [X: {robotPose.x.toFixed(2)}, Y: {robotPose.y.toFixed(2)}]</span>
      </div>

      <div className="flex-1 bg-darkBg rounded border border-borderColor overflow-hidden relative flex items-center justify-center">
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="select-none">
          {/* Draw grid lines */}
          <g stroke="#1f1f22" strokeWidth="0.5">
            {Array.from({ length: 11 }).map((_, i) => {
              const xVal = scaleX(-5 + i);
              return <line key={`x-${i}`} x1={xVal} y1={0} x2={xVal} y2={height} />;
            })}
            {Array.from({ length: 11 }).map((_, i) => {
              const yVal = scaleY(-2 + i);
              return <line key={`y-${i}`} x1={0} y1={yVal} x2={width} y2={yVal} />;
            })}
          </g>

          {/* Draw Rooms */}
          {rooms.map((room) => {
            const rx1 = scaleX(room.x1);
            const ry1 = scaleY(room.y2); // Y coordinate flip
            const rx2 = scaleX(room.x2);
            const ry2 = scaleY(room.y1);
            const w = rx2 - rx1;
            const h = ry2 - ry1;

            return (
              <g key={room.name}>
                <rect
                  x={rx1}
                  y={ry1}
                  width={w}
                  height={h}
                  fill={room.color}
                  stroke="#3f3f46"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                  rx="4"
                />
                <text
                  x={rx1 + 8}
                  y={ry1 + 18}
                  fill="#71717a"
                  fontSize="10"
                  fontWeight="600"
                  letterSpacing="0.05em"
                >
                  {room.name.toUpperCase()}
                </text>
              </g>
            );
          })}

          {/* Draw Landmarks */}
          {landmarks.map((l) => (
            <g key={l.name}>
              <circle cx={scaleX(l.x)} cy={scaleY(l.y)} r="4" fill={l.color} opacity="0.8" />
              <text
                x={scaleX(l.x) + 7}
                y={scaleY(l.y) + 3}
                fill="#a1a1aa"
                fontSize="8"
              >
                {l.name}
              </text>
            </g>
          ))}

          {/* Draw Object Markers */}
          {objects.map((obj) => (
            <g key={obj.name}>
              <circle cx={scaleX(obj.x)} cy={scaleY(obj.y)} r="6" fill={obj.color} opacity="0.9" stroke="#fff" strokeWidth="0.5" />
              <text
                x={scaleX(obj.x) - 15}
                y={scaleY(obj.y) - 10}
                fill="#e4e4e7"
                fontSize="9"
                fontWeight="500"
              >
                {obj.name}
              </text>
            </g>
          ))}

          {/* Draw Path Vector (Active Navigation) */}
          {targetCoords && (
            <line
              x1={scaleX(robotPose.x)}
              y1={scaleY(robotPose.y)}
              x2={scaleX(targetCoords.x)}
              y2={scaleY(targetCoords.y)}
              stroke="#3b82f6"
              strokeWidth="1.5"
              strokeDasharray="5 5"
              className="pulse-active"
            />
          )}

          {/* Draw Robot Base Link */}
          <g transform={`translate(${scaleX(robotPose.x)}, ${scaleY(robotPose.y)})`}>
            {/* Pulsing visual halo when moving */}
            {telemetry.current_action === 'navigating' && (
              <circle cx="0" cy="0" r="14" fill="rgba(59, 130, 246, 0.25)" className="pulse-active" />
            )}
            {/* Robot body */}
            <circle cx="0" cy="0" r="10" fill="#27272a" stroke="#f4f4f5" strokeWidth="2" />
            {/* Heading vector arrow pointer */}
            <line
              x1="0"
              y1="0"
              x2={13 * Math.cos(robotPose.theta)}
              y2={-13 * Math.sin(robotPose.theta)} // SVG Y is inverted
              stroke="#ef4444"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            {/* Tiny center hub */}
            <circle cx="0" cy="0" r="3" fill="#ef4444" />
          </g>
        </svg>
        
        {/* Overlay Legend */}
        <div className="absolute bottom-2 left-2 flex gap-3 text-[9px] bg-[#09090b]/80 px-2 py-1 rounded border border-borderColor">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            <span>Robot Head</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Active Object</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            <span>Landmarks</span>
          </div>
        </div>
      </div>
    </div>
  );
};
export default RobotVisualizer;
