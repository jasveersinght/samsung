import React from 'react';
import { CheckCircle2, PlayCircle, AlertCircle, HelpCircle, RefreshCw } from 'lucide-react';

interface Task {
  id: string;
  name: string;
  action: string;
  parameters: any;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'RETRY';
  dependencies: string[];
  retry_count: number;
  max_retries: number;
  error_message?: string;
}

interface Plan {
  goal: string;
  parsed_params: any;
  tasks: Task[];
  active: boolean;
}

interface ExecutionGraphProps {
  plan: Plan | null;
}

export const ExecutionGraph: React.FC<ExecutionGraphProps> = ({ plan }) => {
  if (!plan) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-panelBg border border-borderColor rounded-lg p-6 text-center text-textMuted">
        <HelpCircle className="w-12 h-12 mb-3 stroke-[1.2] opacity-50" />
        <p className="text-sm">No active task execution. Enter a natural language command to initialize the task planner.</p>
      </div>
    );
  }

  const tasks = plan.tasks || [];
  const completed = tasks.filter(t => t.status === 'SUCCESS').length;
  const remaining = tasks.filter(t => t.status !== 'SUCCESS').length;

  // Helper to map tasks to their ROS 2 interface metadata
  const getRos2Interfaces = (action: string) => {
    switch (action) {
      case 'Locate':
        return {
          type: 'Memory Query',
          interface: 'RoboticsMemory::get_coordinates()',
          topic: 'N/A'
        };
      case 'Navigate':
        return {
          type: 'Nav2 Action',
          interface: '/navigate_to_pose [nav2_msgs/action/NavigateToPose]',
          topic: '/tf, /odom, /cmd_vel'
        };
      case 'Detect':
        return {
          type: 'Perception Node / CV',
          interface: '/object_detection/detect [sensor_msgs/msg/Image]',
          topic: '/camera/image_raw, /perception/bounding_boxes'
        };
      case 'Pick':
      case 'Place':
      case 'Deliver':
      case 'Fill':
        return {
          type: 'MoveIt2 Action',
          interface: '/execute_trajectory [moveit_msgs/action/ExecuteTrajectory]',
          topic: '/joint_states, /controller_manager/robot_state'
        };
      case 'Verify':
        return {
          type: 'Logical Assertion',
          interface: 'VerifyTaskCondition::verify()',
          topic: '/tf_static'
        };
      default:
        return {
          type: 'ROS 2 Interface',
          interface: '/robot_action',
          topic: '/joint_states'
        };
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'RUNNING':
        return <PlayCircle className="w-4 h-4 text-blue-500 animate-pulse shrink-0" />;
      case 'RETRY':
        return <RefreshCw className="w-4 h-4 text-amber-500 animate-spin shrink-0" />;
      case 'FAILED':
        return <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />;
      default:
        return <div className="w-4 h-4 border border-zinc-700 rounded-full shrink-0"></div>;
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'border-emerald-950/60 bg-emerald-950/20 text-emerald-400';
      case 'RUNNING':
        return 'border-blue-900/60 bg-blue-950/30 text-blue-300 ring-1 ring-blue-500/20';
      case 'RETRY':
        return 'border-amber-900/60 bg-amber-950/20 text-amber-400';
      case 'FAILED':
        return 'border-red-950/60 bg-red-950/20 text-red-400';
      default:
        return 'border-zinc-800/80 bg-zinc-900/40 text-zinc-400';
    }
  };

  return (
    <div className="flex flex-col h-full bg-panelBg border border-borderColor rounded-lg p-4 overflow-hidden">
      {/* Header Info */}
      <div className="flex justify-between items-start mb-4 border-b border-borderColor pb-3">
        <div>
          <span className="text-[10px] tracking-wider uppercase font-semibold text-textMuted block">Goal Specification</span>
          <h2 className="text-base font-bold text-textMain capitalize">{plan.goal.replace(/_/g, ' ')}</h2>
        </div>
        <div className="text-right">
          <span className="text-[10px] tracking-wider uppercase font-semibold text-textMuted block">Timeline Metrics</span>
          <span className="text-xs text-textMain font-mono">{completed} Success / {remaining} Left</span>
        </div>
      </div>

      {/* Task List / Timeline Graph */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {tasks.map((task, idx) => {
          const rosInfo = getRos2Interfaces(task.action);
          const isFailed = task.status === 'FAILED';
          const isRunning = task.status === 'RUNNING';
          const isRetry = task.status === 'RETRY';

          return (
            <div
              key={task.id}
              className={`flex flex-col border rounded-md p-3 transition-colors duration-200 ${getStatusClass(task.status)}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getStatusIcon(task.status)}
                  <span className="text-sm font-semibold tracking-wide font-mono">
                    {idx + 1}. {task.name}
                  </span>
                </div>
                {task.retry_count > 0 && (
                  <span className="text-[10px] bg-amber-950/80 border border-amber-800 text-amber-400 px-1.5 py-0.5 rounded font-mono">
                    Retry {task.retry_count} / {task.max_retries}
                  </span>
                )}
              </div>

              {/* Dynamic ROS 2 Integration Telemetry */}
              {(isRunning || isRetry || task.status === 'SUCCESS' || isFailed) && (
                <div className="mt-2.5 pt-2 border-t border-borderColor/50 grid grid-cols-2 gap-2 text-[10px] font-mono text-textMuted">
                  <div>
                    <span className="text-[#888] block">ROS 2 API Service Call:</span>
                    <span className="text-textMain break-all">{rosInfo.interface}</span>
                  </div>
                  <div>
                    <span className="text-[#888] block">Topics Subscribed/Published:</span>
                    <span className="text-textMain break-all">{rosInfo.topic}</span>
                  </div>
                </div>
              )}

              {/* Error log overlay for troubleshooting */}
              {isFailed && task.error_message && (
                <div className="mt-2 p-2 bg-red-950/40 border border-red-900/60 rounded text-[10px] font-mono text-red-300">
                  <span className="font-bold uppercase text-red-400 block mb-0.5">Failure Recovery Triggers:</span>
                  {task.error_message}. Initial search failed. Executing LLM replanning context.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default ExecutionGraph;
