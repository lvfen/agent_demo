type AgentControlsProps = {
  owner: "ai_active" | "human_active" | "ai_paused";
  onTakeOver: () => void;
  onReleaseToAi: () => void;
  onResumeAi: () => void;
};

export function AgentControls({ owner, onTakeOver, onReleaseToAi, onResumeAi }: AgentControlsProps) {
  return (
    <div className="agent-controls">
      <button type="button" onClick={onTakeOver}>
        Take Over
      </button>
      <button type="button" onClick={onReleaseToAi} disabled={owner === "ai_active"}>
        Return to AI
      </button>
      <button type="button" onClick={onResumeAi} disabled={owner !== "ai_paused"}>
        Resume AI
      </button>
    </div>
  );
}
