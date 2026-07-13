import { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, AlertOctagon, Mic, MicOff } from 'lucide-react';
import RobotVisualizer from './components/RobotVisualizer';
import ExecutionGraph from './components/ExecutionGraph';
import StatusPanel from './components/StatusPanel';
import LoggingConsole from './components/LoggingConsole';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  logger: string;
}

const getBackendUrl = () => {
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
};

const getWsUrl = () => {
  if (import.meta.env.VITE_WS_BACKEND_URL) {
    return import.meta.env.VITE_WS_BACKEND_URL;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.hostname}:8000`;
};

export function App() {
  const [command, setCommand] = useState('');
  const [telemetry, setTelemetry] = useState<any>({});
  const [plan, setPlan] = useState<any>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [topicLogs, setTopicLogs] = useState<string[]>([]);
  const [isOnline, setIsOnline] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const wsRef = useRef<WebSocket | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: 'audio/webm' };
      let recorder;
      try {
        recorder = new MediaRecorder(stream, options);
      } catch (e) {
        recorder = new MediaRecorder(stream);
      }
      
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await transcribeAudio(audioBlob);
      };

      recorder.start();
      setIsRecording(true);
      setErrorMsg('');
    } catch (err: any) {
      console.error('Failed to access microphone:', err);
      setErrorMsg(`Microphone access failed: ${err.message || err}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    setLoading(true);
    setErrorMsg('');
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');

      const res = await fetch(`${getBackendUrl()}/api/speech`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      const transcribedText = data.text;
      
      if (transcribedText) {
        setCommand(transcribedText);
        await sendCommand(transcribedText);
      } else {
        throw new Error("Whisper returned empty transcription.");
      }
    } catch (err: any) {
      console.error('Transcription error:', err);
      setErrorMsg(`Transcription failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  // Quick action presets requested in goal criteria
  const presets = [
    "Bring me a glass of water.",
    "Pick up the red bottle.",
    "Go to the kitchen and return."
  ];

  // Initialize Websocket connection
  useEffect(() => {
    connectWebsocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebsocket = () => {
    const wsUrl = `${getWsUrl()}/api/ws`;
    console.log(`Connecting to WebSocket at ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsOnline(true);
      setErrorMsg('');
      console.log('WebSocket connection established.');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.telemetry) setTelemetry(data.telemetry);
        if (data.plan) setPlan(data.plan);
        else setPlan(null);
        setIsPaused(data.is_paused);
        
        // Append new logs to state
        if (data.logs && data.logs.length > 0) {
          setLogs((prev) => [...prev, ...data.logs].slice(-200));
        }
        if (data.topic_logs) {
          setTopicLogs(data.topic_logs);
        }
      } catch (err) {
        console.error('Error parsing websocket payload:', err);
      }
    };

    ws.onclose = () => {
      setIsOnline(false);
      console.log('WebSocket connection closed. Retrying in 3 seconds...');
      setTimeout(connectWebsocket, 3000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket encountered an error:', err);
      ws.close();
    };
  };

  const sendCommand = async (cmdText: string) => {
    if (!cmdText.trim()) return;
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${getBackendUrl()}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText })
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const newPlan = await res.json();
      setPlan(newPlan);
      // Clear logs console on new plan initialization
      setLogs([]);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(`Failed to submit: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  const triggerCancel = async () => {
    try {
      await fetch(`${getBackendUrl()}/api/cancel`, { method: 'POST' });
    } catch (err) {
      console.error('Cancel request failed:', err);
    }
  };

  const triggerPause = async () => {
    try {
      await fetch(`${getBackendUrl()}/api/pause`, { method: 'POST' });
    } catch (err) {
      console.error('Pause request failed:', err);
    }
  };

  const triggerResume = async () => {
    try {
      await fetch(`${getBackendUrl()}/api/resume`, { method: 'POST' });
    } catch (err) {
      console.error('Resume request failed:', err);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-darkBg text-textMain overflow-hidden font-sans select-none">
      {/* Navbar header */}
      <header className="flex justify-between items-center px-6 py-4 bg-panelBg border-b border-borderColor">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse"></span>
          <h1 className="text-lg font-bold tracking-wider uppercase">Robotics Task Planning System</h1>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-textMuted">ROS 2 Master Bridge:</span>
          <span className={`px-2 py-0.5 rounded-full font-semibold ${isOnline ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800 animate-pulse'}`}>
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </header>

      {/* Main Grid Panels */}
      <div className="flex-1 grid grid-rows-[2fr_1fr] gap-4 p-4 overflow-hidden">
        {/* Top half dashboard panels */}
        <div className="grid grid-cols-[1fr_1.8fr_1fr] gap-4 overflow-hidden">
          {/* Left panel: commands input */}
          <div className="flex flex-col h-full bg-panelBg border border-borderColor rounded-lg p-4 justify-between">
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold tracking-wider uppercase text-textMain mb-2">Natural Language Operator</h3>
                <textarea
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="Enter instruction, e.g. 'Bring me a glass of water.'"
                  className="w-full h-24 bg-darkBg border border-borderColor rounded p-2 text-xs font-mono text-textMain placeholder-zinc-600 focus:outline-none focus:border-zinc-500 resize-none"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendCommand(command);
                    }
                  }}
                />
              </div>

              {/* Run submission buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => sendCommand(command)}
                  disabled={loading || !isOnline}
                  className="flex-1 bg-textMain hover:bg-zinc-300 disabled:bg-zinc-800 disabled:text-zinc-600 text-darkBg py-2 rounded text-xs font-bold transition-all"
                >
                  {loading ? 'PLANNING...' : 'SUBMIT COMMAND'}
                </button>
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={loading || !isOnline}
                  type="button"
                  title={isRecording ? "Stop recording and transcribe" : "Start voice command recording (Whisper)"}
                  className={`flex items-center justify-center px-3 py-2 rounded transition-all border ${
                    isRecording 
                      ? 'bg-red-950 text-red-400 border-red-800 animate-pulse' 
                      : 'bg-zinc-800 text-textMain border-borderColor hover:bg-zinc-700'
                  }`}
                >
                  {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              </div>

              {errorMsg && (
                <div className="flex items-center gap-2 p-2 bg-red-950/40 border border-red-900/60 rounded text-[10px] text-red-400 font-mono">
                  <AlertOctagon className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Preset buttons */}
              <div className="space-y-2 pt-2 border-t border-borderColor">
                <span className="text-[10px] tracking-wider uppercase font-semibold text-textMuted block">Preset Missions</span>
                <div className="flex flex-col gap-1.5">
                  {presets.map((preset) => (
                    <button
                      key={preset}
                      onClick={() => {
                        setCommand(preset);
                        sendCommand(preset);
                      }}
                      disabled={!isOnline}
                      className="text-left w-full bg-darkBg border border-borderColor hover:bg-zinc-800 disabled:opacity-50 text-textMuted hover:text-textMain px-2.5 py-1.5 rounded text-xs font-mono transition-colors"
                    >
                      &gt; {preset}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Run states navigation control */}
            <div className="pt-4 border-t border-borderColor space-y-2">
              <span className="text-[10px] tracking-wider uppercase font-semibold text-textMuted block">Execution Controls</span>
              <div className="grid grid-cols-3 gap-2">
                {isPaused ? (
                  <button
                    onClick={triggerResume}
                    disabled={!plan}
                    className="flex justify-center items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 text-textMain py-2 rounded text-xs border border-zinc-700 transition"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Resume</span>
                  </button>
                ) : (
                  <button
                    onClick={triggerPause}
                    disabled={!plan}
                    className="flex justify-center items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 text-textMain py-2 rounded text-xs border border-zinc-700 transition"
                  >
                    <Pause className="w-3.5 h-3.5 fill-current" />
                    <span>Pause</span>
                  </button>
                )}
                <button
                  onClick={triggerCancel}
                  disabled={!plan}
                  className="col-span-2 flex justify-center items-center gap-1.5 bg-red-950/60 border border-red-800 hover:bg-red-900/60 text-red-300 py-2 rounded text-xs transition"
                >
                  <Square className="w-3 h-3 fill-current" />
                  <span>Cancel Execution</span>
                </button>
              </div>
            </div>
          </div>

          {/* Center panel: dynamic execution graph */}
          <div className="h-full overflow-hidden">
            <ExecutionGraph plan={plan} />
          </div>

          {/* Right panel: dynamic localization map */}
          <div className="h-full overflow-hidden">
            <RobotVisualizer telemetry={telemetry} plan={plan} />
          </div>
        </div>

        {/* Bottom half: console logs terminal & status panel */}
        <div className="grid grid-cols-[3fr_1fr] gap-4 overflow-hidden">
          <div className="h-full overflow-hidden">
            <LoggingConsole logs={logs} topicLogs={topicLogs} />
          </div>
          <div className="h-full overflow-hidden">
            <StatusPanel telemetry={telemetry} isOnline={isOnline} isPaused={isPaused} />
          </div>
        </div>
      </div>
    </div>
  );
}
export default App;
