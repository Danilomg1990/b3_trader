// Configuração da URL da API
const API_BASE_URL = "http://127.0.0.1:8000";
let progressInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("analyzeBtn").addEventListener("click", analyzeStock);

  // Tecla Enter nos inputs
  document.getElementById("quoteInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") getQuote();
  });

  document.getElementById("tickerInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") analyzeStock();
  });
});

// ========================================================
// COTAÇÃO RÁPIDA
// ========================================================
async function getQuote() {
  const ticker = document
    .getElementById("quoteInput")
    .value.toUpperCase()
    .trim();

  if (!ticker) return alert("⚠️ Digite o código do ativo!");

  try {
    const res = await fetch(`${API_BASE_URL}/quote/${ticker}`);
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Ativo não encontrado");
    }

    const data = await res.json();
    const fmt = new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    });

    document.getElementById("qPrice").innerText = fmt.format(data.price);
    document.getElementById("qLow").innerText = fmt.format(data.low_52k);
    document.getElementById("qHigh").innerText = fmt.format(data.high_52k);
    document.getElementById("qAvg").innerText = fmt.format(data.avg_52k);

    document.getElementById("quoteResult").classList.remove("hidden");
  } catch (e) {
    alert(e.message);
  }
}

// ========================================================
// ANÁLISE IA (PRINCIPAL)
// ========================================================
async function analyzeStock() {
  const ticker = document
    .getElementById("tickerInput")
    .value.toUpperCase()
    .trim();
  const days = document.getElementById("daysInput").value;
  const timeframe = document.getElementById("timeframeInput").value;
  const profile = document.getElementById("profileInput").value;

  if (!ticker) return alert("⚠️ Digite o código da ação!");

  // UI Loading
  const btn = document.getElementById("analyzeBtn");
  btn.disabled = true;
  btn.innerText = "Processando...";
  document.getElementById("loading").classList.remove("hidden");

  startProgressBar();

  try {
    // 1. Sincroniza Dados
    await fetch(`${API_BASE_URL}/sync/${ticker}`, { method: "POST" });

    // 2. Executa Análise
    const params = new URLSearchParams({ days, timeframe, profile });
    const res = await fetch(
      `${API_BASE_URL}/analyze/${ticker}?${params.toString()}`
    );

    if (!res.ok) throw new Error("Erro na IA ou dados insuficientes");

    const data = await res.json();

    finishProgressBar();

    // --- CORREÇÃO PARA O COMPUTADOR ---
    // Salva no LocalStorage (Disco do Navegador)
    localStorage.setItem("chartData", JSON.stringify(data));

    setTimeout(() => {
      // Redireciona para a página do gráfico
      window.location.href = "/app/chart.html";
    }, 800);
  } catch (error) {
    console.error(error);
    alert(error.message);
    stopProgressBar();
    document.getElementById("loading").classList.add("hidden");
    btn.disabled = false;
    btn.innerText = "Processar e Abrir Gráfico 📊";
  }
}

// ========================================================
// BARRA DE PROGRESSO
// ========================================================
function startProgressBar() {
  const bar = document.getElementById("loadingBar");
  const text = document.getElementById("loadingText");
  let width = 0;
  bar.style.width = "0%";

  if (progressInterval) clearInterval(progressInterval);

  progressInterval = setInterval(() => {
    if (width < 90) {
      width += Math.random() * 10;
      if (width > 90) width = 90;
      bar.style.width = width + "%";

      if (width > 20) text.innerText = "Baixando dados da B3...";
      if (width > 40) text.innerText = "Calculando Indicadores Técnicos...";
      if (width > 60) text.innerText = "Processando Modelos Quantitativos...";
      if (width > 80) text.innerText = "Gerando Projeção...";
    }
  }, 200);
}

function finishProgressBar() {
  if (progressInterval) clearInterval(progressInterval);
  document.getElementById("loadingBar").style.width = "100%";
  document.getElementById("loadingText").innerText =
    "Sucesso! Abrindo Gráfico...";
}

function stopProgressBar() {
  if (progressInterval) clearInterval(progressInterval);
}
