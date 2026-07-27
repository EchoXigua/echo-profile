import { projects } from "@/content/projects";
import type { FeaturedProject } from "@/types/content";

function ProjectStage({
  index,
  project,
}: {
  index: "03" | "04";
  project: FeaturedProject;
}) {
  const isVoya = project.slug === "voya";

  return (
    <section
      className={`section story-stage project-stage ${isVoya ? "stage-right" : ""}`}
      data-stage={project.slug}
      id={project.slug}
    >
      <div className="section-inner stage-layout">
        <article
          className="stage-copy project-panel"
          data-stage-copy
          data-tone={project.tone}
        >
          <p className="stage-coordinate">
            {index} / {isVoya ? "ROUTE SIGNAL" : "LIFE SIGNAL"}
          </p>
          <p className="section-kicker">
            {index} / Selected Work · {project.stage}
          </p>
          <h2 className="section-title">{project.name}</h2>
          <p className="section-copy">{project.description}</p>
          <div className="tag-list">
            {project.tags.map((tag) => (
              <span className="tag" key={tag}>
                {tag}
              </span>
            ))}
          </div>
          <a
            className="project-link"
            href={project.href}
            target="_blank"
            rel="noreferrer"
          >
            在 byecho.cn 查看完整项目 →
          </a>
        </article>
      </div>
    </section>
  );
}

export function LeanMateSection() {
  return <ProjectStage index="03" project={projects[0]} />;
}

export function VoyaSection() {
  return <ProjectStage index="04" project={projects[1]} />;
}
