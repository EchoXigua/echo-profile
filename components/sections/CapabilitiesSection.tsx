import { capabilities } from "@/content/capabilities";

export function CapabilitiesSection() {
  return (
    <section
      className="section story-stage"
      data-stage="engineering"
      id="engineering"
    >
      <div className="section-inner stage-layout">
        <div className="stage-copy engineering-copy" data-stage-copy>
          <p className="stage-coordinate">02 / SYSTEM CHECK</p>
          <p className="section-kicker">02 / AI Engineering</p>
          <h2 className="section-title">I build with AI.</h2>
          <p className="section-copy">
            把 AI 变成可控的研发方式，也把模型能力变成可信、可验证的产品体验。
          </p>
          <div className="capability-list">
            {capabilities.map((capability, index) => (
              <article className="capability-row" key={capability.title}>
                <span>0{index + 1}</span>
                <div>
                  <h3>{capability.title}</h3>
                  <p>{capability.description}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
