import { SiteHeader } from "@/components/layout/SiteHeader";
import { StageRail } from "@/components/layout/StageRail";
import { LazyEchoScene } from "@/components/scene/LazyEchoScene";
import { AboutSection } from "@/components/sections/AboutSection";
import { CapabilitiesSection } from "@/components/sections/CapabilitiesSection";
import { ContactSection } from "@/components/sections/ContactSection";
import { HeroSection } from "@/components/sections/HeroSection";
import {
  LeanMateSection,
  VoyaSection,
} from "@/components/sections/ProjectsSection";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <LazyEchoScene />
      <StageRail />
      <main id="scroll-story">
        <HeroSection />
        <AboutSection />
        <CapabilitiesSection />
        <LeanMateSection />
        <VoyaSection />
        <ContactSection />
      </main>
    </>
  );
}
