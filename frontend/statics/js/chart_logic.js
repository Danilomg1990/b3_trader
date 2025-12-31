document.addEventListener("DOMContentLoaded", () => {
  // --- CORREÇÃO PARA O COMPUTADOR ---
  // Busca do localStorage (Disco) em vez da memória temporária
  const storedData = localStorage.getItem("chartData");

  if (!storedData) {
    alert("⚠️ Nenhum dado de análise encontrado. Você será redirecionado.");
    window.location.href = "/app/"; // Volta para o início
    return;
  }

  try {
    const data = JSON.parse(storedData);
    renderPage(data);
  } catch (e) {
    console.error("Erro ao ler dados:", e);
    alert("Dados corrompidos. Tente analisar novamente.");
    window.location.href = "/app/";
  }
});

function renderPage(data) {
  const fmt = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  // Preenche Cabeçalho
  document.getElementById("chartTitle").innerHTML = `
    <span class="text-yellow-400">${data.ticker}</span> 
    <span class="text-gray-500 text-lg mx-2">|</span> 
    Perfil ${data.profile || "Padrão"}
  `;

  document.getElementById("predPrice").innerText = fmt.format(
    data.predicted_price
  );

  const signalEl = document.getElementById("aiSignal");
  signalEl.innerText = data.signal;

  if (data.signal.includes("COMPRA")) {
    signalEl.className =
      "text-2xl font-bold text-green-400 drop-shadow-[0_0_10px_rgba(74,222,128,0.5)]";
  } else if (data.signal.includes("VENDA")) {
    signalEl.className =
      "text-2xl font-bold text-red-500 drop-shadow-[0_0_10px_rgba(248,113,113,0.5)]";
  } else {
    signalEl.className = "text-2xl font-bold text-gray-400";
  }

  // Configuração do Gráfico
  const cData = data.chart_data;

  const candles = cData.candles.map((c) => ({
    x: c.x,
    y: [
      c.y[0].toFixed(2),
      c.y[1].toFixed(2),
      c.y[2].toFixed(2),
      c.y[3].toFixed(2),
    ],
  }));

  const mapLine = (arr) =>
    arr
      ? arr.map((p) => ({ x: p.x, y: p.y ? parseFloat(p.y.toFixed(2)) : null }))
      : [];

  const seriesData = [{ name: "Preço", type: "candlestick", data: candles }];

  if (cData.vwap && cData.vwap.length > 0)
    seriesData.push({ name: "VWAP", type: "line", data: mapLine(cData.vwap) });
  if (cData.sma_14 && cData.sma_14.length > 0)
    seriesData.push({
      name: "SMA 14",
      type: "line",
      data: mapLine(cData.sma_14),
    });
  if (cData.sma_50 && cData.sma_50.length > 0)
    seriesData.push({
      name: "SMA 50",
      type: "line",
      data: mapLine(cData.sma_50),
    });

  const options = {
    series: seriesData,
    chart: {
      type: "candlestick",
      height: "100%",
      background: "#111827",
      toolbar: {
        show: true,
        tools: { download: true, selection: true, zoom: true, pan: true },
      },
      animations: { enabled: false },
    },
    title: { text: "", align: "left", style: { color: "#fff" } },
    stroke: { width: [1, 2, 2, 2], curve: "smooth", dashArray: [0, 5, 0, 0] },
    colors: ["#00E396", "#F59E0B", "#EC4899", "#3B82F6"],
    xaxis: {
      type: "datetime",
      labels: { style: { colors: "#9CA3AF" } },
      tooltip: { enabled: true },
    },
    yaxis: {
      opposite: true,
      labels: {
        style: { colors: "#9CA3AF" },
        formatter: (val) => (val ? val.toFixed(2) : val),
      },
    },
    grid: { borderColor: "#374151", strokeDashArray: 4 },
    theme: { mode: "dark" },
    tooltip: {
      theme: "dark",
      shared: true,
      intersect: false,
      y: { formatter: (val) => (val ? "R$ " + val.toFixed(2) : "") },
    },
    plotOptions: {
      candlestick: {
        colors: { upward: "#10B981", downward: "#EF4444" },
        wick: { useFillColor: true },
      },
    },
  };

  const chart = new ApexCharts(document.querySelector("#stockChart"), options);
  chart.render();
}
