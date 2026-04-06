import { FormEvent, useState } from "react";

type MessageComposerProps = {
  placeholder: string;
  submitLabel: string;
  disabled?: boolean;
  onSubmit: (text: string) => void;
};

export function MessageComposer({ placeholder, submitLabel, disabled, onSubmit }: MessageComposerProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = value.trim();
    if (!text || disabled) {
      return;
    }
    onSubmit(text);
    setValue("");
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <textarea
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
      />
      <button type="submit" disabled={disabled}>
        {submitLabel}
      </button>
    </form>
  );
}
