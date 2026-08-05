(() => {
  const browserLanguage = (navigator.languages?.[0] || navigator.language || "en").toLowerCase();
  const isChinese = browserLanguage.startsWith("zh");

  document.documentElement.lang = isChinese ? "zh-CN" : "en";
  document.title = isChinese
    ? "Open-Rosalind · 生物医学科研智能体"
    : "Open-Rosalind · Biomedical Research Agent";

  const description = document.querySelector('meta[name="description"]');
  if (description) {
    description.content = isChinese
      ? "Open-Rosalind：面向生物医学科研的可追溯 AI Agent，连接专业 Skills、数据服务与可复现工作流。"
      : "Open-Rosalind is a traceable AI agent for biomedical research, connecting domain skills, data services, and reproducible workflows.";
  }

  const attribute = isChinese ? "zh" : "en";
  document.querySelectorAll(`[data-${attribute}]`).forEach((element) => {
    element.textContent = element.dataset[attribute];
  });
})();
