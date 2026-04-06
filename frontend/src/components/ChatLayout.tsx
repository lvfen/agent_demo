import type { ReactNode } from "react";

type ChatLayoutProps = {
  title: string;
  subtitle?: string;
  controls?: ReactNode;
  children: ReactNode;
};

export function ChatLayout({ title, subtitle, controls, children }: ChatLayoutProps) {
  return (
    <main className="shell">
      <section className="panel">
        <header className="panel-header">
          <div>
            <p className="eyebrow">{subtitle ?? "Single conversation demo"}</p>
            <h1>{title}</h1>
          </div>
          {controls ? <div className="header-controls">{controls}</div> : null}
        </header>
        {children}
      </section>
    </main>
  );
}
