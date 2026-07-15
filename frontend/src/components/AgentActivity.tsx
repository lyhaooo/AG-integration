import { useEffect, useRef, useState } from "react";
import type { ActivityEvent, MethodStatus } from "../types";

interface Props {
  stage: MethodStatus["activity_stage"];
  detail: MethodStatus["activity_detail"];
  agent: string | null;
  events: ActivityEvent[];
}

const STAGE_LABELS = {
  debugging: "算子自动调试中",
  optimization: "算子自动优化中",
} as const;

export default function AgentActivity({ stage, detail, agent, events }: Props) {
  const seenEventIds = useRef(new Set<number>());
  const [pendingEvents, setPendingEvents] = useState<ActivityEvent[]>([]);
  const [displayedEvent, setDisplayedEvent] = useState<ActivityEvent | null>(null);

  useEffect(() => {
    const unseen = events.filter((event) => !seenEventIds.current.has(event.id));
    if (unseen.length === 0) return;
    unseen.forEach((event) => seenEventIds.current.add(event.id));
    setPendingEvents((current) => [...current, ...unseen]);
  }, [events]);

  useEffect(() => {
    if (displayedEvent || pendingEvents.length === 0) return;
    setDisplayedEvent(pendingEvents[0]);
    setPendingEvents((current) => current.slice(1));
  }, [displayedEvent, pendingEvents]);

  useEffect(() => {
    if (!displayedEvent) return;
    const timer = window.setTimeout(() => setDisplayedEvent(null), 2000);
    return () => window.clearTimeout(timer);
  }, [displayedEvent]);

  const displayedStage = displayedEvent?.stage ?? stage;
  const displayedDetail = displayedEvent?.detail ?? detail;
  const displayedAgent = displayedEvent?.agent ?? agent;
  const label = displayedStage === "generator"
    ? displayedDetail === "combination" ? "算子自动组合中" : "算子自动生成中"
    : displayedStage ? STAGE_LABELS[displayedStage] : "多智能体协作准备中";

  return (
    <div className="agent-activity" role="status" aria-live="polite">
      <div className="agent-activity-header">
        <div className="agent-activity-label">
          <span className="agent-activity-pulse" />
          <strong>{label}</strong>
        </div>
        {displayedAgent && <span className="agent-name">{displayedAgent} Agent</span>}
      </div>
      <div className="agent-progress-track" aria-hidden="true">
        <div className="agent-progress-flow" />
      </div>
    </div>
  );
}
