document.addEventListener("DOMContentLoaded", () => {
  // 1. Recupera os dados salvos no navegador (LocalStorage)
  const storedData = localStorage.getItem("chartData");

  // Se não tiver dados (o usuário tentou abrir a página direto sem passar pela análise)
  if (!storedData) {
    alert("Nenhum dado de análise encontrado. Você será redirecionado.");
    window.location.href = "/"; // Volta para o início
    return;
  }

  // 2. Converte o texto de volta para objeto JSON
  const data = JSON.parse(storedData);

  // 3. Desenha a tela
  renderPage(data);
});

function renderPage(data) {
  const fmt = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  // --- Preenche os Textos da Barra Superior ---
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

  // --- Prepara os Dados para o ApexCharts ---
  const cData = data.chart_data;

  // Mapeia Velas
  const candles = cData.candles.map((c) => ({
    x: c.x,
    y: [
      c.y[0].toFixed(2),
      c.y[1].toFixed(2),
      c.y[2].toFixed(2),
      c.y[3].toFixed(2),
    ],
  }));

  // Função segura para mapear linhas (trata nulos)
  const mapLine = (arr) =>
    arr
      ? arr.map((p) => ({ x: p.x, y: p.y ? parseFloat(p.y.toFixed(2)) : null }))
      : [];

  const seriesData = [{ name: "Preço", type: "candlestick", data: candles }];

  // Adiciona linhas apenas se existirem dados
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

  // --- Configuração do Gráfico ---
  const options = {
    series: seriesData,
    chart: {
      type: "candlestick",
      height: "100%",
      background: "#111827", // Fundo Dark (Gray-900)
      toolbar: {
        show: true,
        tools: { download: true, selection: true, zoom: true, pan: true },
      },
      animations: { enabled: false }, // Desativa animação para renderizar instantâneo
    },
    title: {
      text: "",
      align: "left",
      style: { color: "#fff" },
    },
    stroke: {
      width: [1, 2, 2, 2],
      curve: "smooth",
      dashArray: [0, 5, 0, 0], // VWAP tracejada
    },
    colors: [
      "#00E396", // Candles (Verde base, mas o plotOptions sobrescreve)
      "#F59E0B", // VWAP (Laranja)
      "#EC4899", // SMA 14 (Rosa)
      "#3B82F6", // SMA 50 (Azul)
    ],
    xaxis: {
      type: "datetime",
      labels: { style: { colors: "#9CA3AF" } },
      tooltip: { enabled: true },
    },
    yaxis: {
      opposite: true, // Eixo Y na direita (padrão trader)
      labels: {
        style: { colors: "#9CA3AF" },
        formatter: (val) => {
          return val ? val.toFixed(2) : val;
        },
      },
    },
    grid: {
      borderColor: "#374151",
      strokeDashArray: 4,
    },
    theme: { mode: "dark" },

    // Tooltip Customizado
    tooltip: {
      theme: "dark",
      shared: true,
      intersect: false,
      y: {
        formatter: function (val) {
          return val ? "R$ " + val.toFixed(2) : val;
        },
      },
    },

    // Cores das Velas
    plotOptions: {
      candlestick: {
        colors: {
          upward: "#10B981", // Verde Tailwind
          downward: "#EF4444", // Vermelho Tailwind
        },
        wick: { useFillColor: true },
      },
    },
  };

  // Renderiza
  const chart = new ApexCharts(document.querySelector("#stockChart"), options);
  chart.render();
}
