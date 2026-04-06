import type { TranscriptMessage } from "../types";

type MessageListProps = {
  messages: TranscriptMessage[];
  transcriptRoleMap?: Partial<Record<TranscriptMessage["role"], string>>;
};

export function MessageList({ messages, transcriptRoleMap }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => (
        <article key={message.id} className={`bubble bubble-${message.role}`}>
          <p className="bubble-author">{transcriptRoleMap?.[message.role] ?? message.role}</p>
          <p>{message.text}</p>
        </article>
      ))}
    </div>
  );
}
