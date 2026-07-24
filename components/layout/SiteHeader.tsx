import { navigation } from "@/content/navigation";

export function SiteHeader() {
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="返回 Echo 个人主页顶部">
        Echo
      </a>
      <nav className="site-nav" aria-label="主要导航">
        {navigation.map((item) => (
          <a key={item.href} href={item.href}>
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
