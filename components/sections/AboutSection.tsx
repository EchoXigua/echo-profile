import { profile } from "@/content/profile";

export function AboutSection() {
  return (
    <section className="section" id="about">
      <div className="section-inner">
        <p className="section-kicker">01 / About</p>
        <h2 className="section-title">{profile.aboutTitle}</h2>
        <p className="section-copy">{profile.about}</p>
      </div>
    </section>
  );
}
