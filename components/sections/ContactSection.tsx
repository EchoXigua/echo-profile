export function ContactSection() {
  return (
    <section className="section story-stage contact-stage" data-stage="contact" id="contact">
      <div className="section-inner stage-layout">
        <div className="stage-copy contact-panel" data-stage-copy>
          <p className="stage-coordinate">05 / DOCKING</p>
          <p className="section-kicker">05 / Contact</p>
          <h2 className="section-title">正在寻找前端与 AI 应用全栈方向的新机会。</h2>
          <p className="section-copy">
            求职、产品合作或 AI 应用研发交流，都可以从这里开始。
          </p>
          <div className="contact-actions">
            <a className="button button-primary" href="https://byecho.cn" target="_blank" rel="noreferrer">
              查看完整作品
            </a>
            <a className="button" href="#top">
              返回轨道起点
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
