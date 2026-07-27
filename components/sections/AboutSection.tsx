import { profile } from "@/content/profile";

export function AboutSection() {
  return (
    <section className="section story-stage stage-right" data-stage="about" id="about">
      <div className="section-inner stage-layout">
        <div className="stage-copy" data-stage-copy>
          <p className="stage-coordinate">01 / TRAJECTORY</p>
          <p className="section-kicker">01 / About</p>
          <h2 className="section-title">{profile.aboutTitle}</h2>
          <p className="section-copy">{profile.about}</p>
          <dl className="stage-facts">
            <div>
              <dt>起点</dt>
              <dd>前端体验与工程基础</dd>
            </div>
            <div>
              <dt>方向</dt>
              <dd>AI 应用全栈构建</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
