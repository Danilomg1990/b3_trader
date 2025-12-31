const API_BASE_URL = "http://127.0.0.1:8000";
let progressInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("analyzeBtn").addEventListener("click", analyzeStock);
});

// --- FUNÇÃO DE COTAÇÃO RÁPIDA (REQ 2) ---
async function getQuote() {
  const ticker = document
    .getElementById("quoteInput")
    .value.toUpperCase()
    .trim();
  if (!ticker) return alert("Digite o ativo!");

  try {
    const res = await fetch(`${API_BASE_URL}/quote/${ticker}`);
    if (!res.ok) throw new Error("Ativo não encontrado");
    const data = await res.json();

    // Preenche os dados
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

// --- FUNÇÃO DE ANÁLISE IA (REQ 1 & 3) ---
async function analyzeStock() {
  const ticker = document
    .getElementById("tickerInput")
    .value.toUpperCase()
    .trim();
  const days = document.getElementById("daysInput").value;
  const timeframe = document.getElementById("timeframeInput").value;
  const profile = document.getElementById("profileInput").value; // Perfil Selecionado

  if (!ticker) return alert("Digite o código da ação!");

  // UI Loading
  document.getElementById("loading").classList.remove("hidden");
  startProgressBar();

  try {
    await fetch(`${API_BASE_URL}/sync/${ticker}`, { method: "POST" });

    const params = new URLSearchParams({ days, timeframe, profile });

    const res = await fetch(
      `${API_BASE_URL}/analyze/${ticker}?${params.toString()}`
    );
    if (!res.ok) throw new Error("Erro na IA");
    const data = await res.json();

    finishProgressBar();

    // --- MUDANÇA DE PÁGINA ---
    // Salva os dados no navegador para a próxima página ler
    localStorage.setItem("chartData", JSON.stringify(data));

    setTimeout(() => {
      window.location.href = "chart.html"; // Redireciona para a página do gráfico
    }, 800);
  } catch (error) {
    console.error(error);
    alert(error.message);
    stopProgressBar();
    document.getElementById("loading").classList.add("hidden");
  }
}

// ... (Mantenha as funções startProgressBar, finishProgressBar, stopProgressBar IGUAIS) ...
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
      if (width > 30) text.innerText = "Calculando Modelos Quantitativos...";
      if (width > 60) text.innerText = "Gerando Projeção...";
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
