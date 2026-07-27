import { profile } from "@/content/profile";

export function HeroSection() {
  return (
    <section className="section story-stage hero" data-stage="hero" id="top">
      <div className="section-inner stage-layout">
        <div className="stage-copy hero-copy" data-stage-copy>
          <p className="stage-coordinate">00 / ORBIT ENTRY</p>
          <h1>{profile.name}</h1>
          <p className="hero-eyebrow">{profile.role}</p>
          <p className="hero-statement">{profile.heroAccent}</p>
          <p className="hero-description">{profile.summary}</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#leanmate">
              查看精选项目
            </a>
            <a className="button" href="#contact">
              联系 Echo
            </a>
          </div>
          <a className="scroll-cue" href="#about">
            <span>Scroll to explore</span>
            <span aria-hidden="true">↓</span>
          </a>
        </div>
      </div>
    </section>
  );
}
