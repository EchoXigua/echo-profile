import { LazyEchoScene } from "@/components/scene/LazyEchoScene";
import { profile } from "@/content/profile";

export function HeroSection() {
  return (
    <section className="section hero" id="top">
      <div className="section-inner hero-grid">
        <div>
          <p className="hero-eyebrow">{profile.role}</p>
          <h1>
            {profile.name}
            <span>{profile.heroAccent}</span>
          </h1>
          <p className="hero-description">{profile.summary}</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#projects">
              查看精选项目
            </a>
            <a className="button" href="#contact">
              联系 Echo
            </a>
          </div>
        </div>
        <LazyEchoScene />
      </div>
    </section>
  );
}
