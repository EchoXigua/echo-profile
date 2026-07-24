import { projects } from "@/content/projects";

export function ProjectsSection() {
  return (
    <section className="section" id="projects">
      <div className="section-inner">
        <p className="section-kicker">03 / Selected Work</p>
        <h2 className="section-title">用真实项目，证明完整的产品能力。</h2>
        <div className="card-grid">
          {projects.map((project, index) => (
            <article className="card project-card" data-tone={project.tone} key={project.slug}>
              <span className="card-index">0{index + 1} / {project.stage}</span>
              <h3>{project.name}</h3>
              <p>{project.description}</p>
              <div className="tag-list">
                {project.tags.map((tag) => (
                  <span className="tag" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
              <a className="project-link" href={project.href} target="_blank" rel="noreferrer">
                在 byecho.cn 查看完整项目 →
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
