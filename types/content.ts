export interface Capability {
  title: string;
  description: string;
  tags: string[];
}

export interface FeaturedProject {
  slug: "leanmate" | "voya";
  name: string;
  stage: string;
  tone: "leanmate" | "voya";
  description: string;
  tags: string[];
  href: string;
}
