import { capabilities } from "@/content/capabilities";

export function CapabilitiesSection() {
  return (
    <section className="section" id="capabilities">
      <div className="section-inner">
        <p className="section-kicker">02 / AI Engineering</p>
        <h2 className="section-title">I don&apos;t just use AI. I build with it.</h2>
        <p className="section-copy">
          把 AI 变成可控的研发方式，也把模型能力变成可信、可验证的产品体验。
        </p>
        <div className="card-grid">
          {capabilities.map((capability, index) => (
            <article className="card" key={capability.title}>
              <span className="card-index">0{index + 1}</span>
              <h3>{capability.title}</h3>
              <p>{capability.description}</p>
              <div className="tag-list">
                {capability.tags.map((tag) => (
                  <span className="tag" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
