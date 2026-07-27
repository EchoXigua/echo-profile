const stages = [
  { label: "Hero", href: "#top" },
  { label: "About", href: "#about" },
  { label: "Engineering", href: "#engineering" },
  { label: "LeanMate", href: "#leanmate" },
  { label: "Voya", href: "#voya" },
  { label: "Contact", href: "#contact" },
] as const;

const orbitLabels = [
  { stage: 2, label: "Engineering", tone: "engineering" },
  { stage: 3, label: "LeanMate", tone: "leanmate" },
  { stage: 4, label: "Voya", tone: "voya" },
  { stage: 5, label: "Contact", tone: "contact" },
] as const;

export function StageRail() {
  return (
    <>
      <div className="orbit-labels" aria-hidden="true">
        {orbitLabels.map((item) => (
          <span
            className={`orbit-label orbit-label-${item.tone}`}
            data-orbit-label={item.stage}
            key={item.label}
          >
            {item.label}
          </span>
        ))}
      </div>
      <nav className="stage-rail" aria-label="滚动章节">
        {stages.map((stage, index) => (
          <a
            className={index === 0 ? "is-active" : undefined}
            data-stage-marker
            href={stage.href}
            key={stage.href}
          >
            <span>0{index}</span>
            <span>{stage.label}</span>
          </a>
        ))}
      </nav>
    </>
  );
}
