import { useState, useCallback, useRef } from "react";
import { api } from "@/services/api";

export interface AgentEvent {
  agent_name: string;
  ticker?: string;
  signal?: string;
  confidence?: number;
  reasoning?: string;
  status?: string;
}

export interface StreamState {
  isRunning: boolean;
  events: AgentEvent[];
  decisions: Record<string, { action: string; quantity: number; confidence: number; reasoning: string }> | null;
  error: string | null;
  runId: number | null;
}

export function useAnalysisStream() {
  const [state, setState] = useState<StreamState>({
    isRunning: false, events: [], decisions: null, error: null, runId: null,
  });
  const esRef = useRef<EventSource | null>(null);

  const startRun = useCallback(async (config: {
    portfolio_id: number; model_name: string; model_provider: string;
    selected_analysts: string[]; start_date: string; end_date: string;
  }) => {
    setState({ isRunning: true, events: [], decisions: null, error: null, runId: null });
    try {
      const { run_id } = await api.analysis.run(config);
      setState((s) => ({ ...s, runId: run_id }));
      const es = new EventSource(api.analysis.streamUrl(run_id));
      esRef.current = es;

      es.addEventListener("agent_start", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, events: [...s.events, data] }));
      });
      es.addEventListener("agent_complete", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({
          ...s,
          events: [...s.events.filter((ev) => !(ev.agent_name === data.agent_name && !ev.signal)), data],
        }));
      });
      es.addEventListener("run_complete", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, isRunning: false, decisions: data.decisions }));
        es.close();
      });
      es.addEventListener("run_error", (e) => {
        const data = JSON.parse(e.data);
        setState((s) => ({ ...s, isRunning: false, error: data.error }));
        es.close();
      });
      es.onerror = () => {
        setState((s) => ({ ...s, isRunning: false, error: "Connection lost" }));
        es.close();
      };
    } catch (err: unknown) {
      setState((s) => ({ ...s, isRunning: false, error: err instanceof Error ? err.message : "Failed to start" }));
    }
  }, []);

  const cancel = useCallback(() => {
    esRef.current?.close();
    setState((s) => ({ ...s, isRunning: false }));
  }, []);

  return { ...state, startRun, cancel };
}
