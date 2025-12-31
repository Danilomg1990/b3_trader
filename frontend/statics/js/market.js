const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  loadMarketOverview();
});

async function loadMarketOverview() {
  const grid = document.getElementById("marketGrid");
  const loading = document.getElementById("marketLoading");

  try {
    const res = await fetch(`${API_BASE_URL}/market/overview`);
    if (!res.ok) throw new Error("Falha ao carregar mercado");

    const data = await res.json();

    loading.classList.add("hidden");
    grid.classList.remove("hidden");

    // Limpa grid
    grid.innerHTML = "";

    // Itera sobre as categorias (Bancos, Petróleo, etc.)
    for (const [category, assets] of Object.entries(data)) {
      const card = createSectorCard(category, assets);
      grid.appendChild(card);
    }
  } catch (error) {
    console.error(error);
    loading.innerHTML = `<p class="text-red-500">Erro ao carregar dados. Tente atualizar a página.</p>`;
  }
}

function createSectorCard(title, assets) {
  const div = document.createElement("div");
  div.className =
    "bg-gray-800 rounded-xl shadow-lg border border-gray-700 overflow-hidden hover:border-gray-500 transition";

  // Cabeçalho do Card
  let headerColor = "bg-gray-750";
  if (title.includes("Cripto")) headerColor = "bg-purple-900/40";
  if (title.includes("Agro")) headerColor = "bg-green-900/40";
  if (title.includes("Imobiliário")) headerColor = "bg-blue-900/40";

  const header = `
        <div class="${headerColor} p-4 border-b border-gray-700">
            <h3 class="font-bold text-gray-200">${title}</h3>
        </div>
    `;

  // Lista de Ativos
  let listHtml = '<div class="divide-y divide-gray-700">';

  assets.forEach((asset) => {
    const isPositive = asset.change >= 0;
    const colorClass = isPositive ? "text-green-400" : "text-red-400";
    const arrow = isPositive ? "▲" : "▼";
    const sign = isPositive ? "+" : "";

    // Formata moeda (USD ou BRL)
    const currency = title.includes("Cripto") ? "USD" : "BRL";
    const fmt = new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: currency,
    });

    listHtml += `
            <div class="p-3 flex justify-between items-center hover:bg-gray-750 transition">
                <span class="font-bold text-sm text-white">${
                  asset.ticker
                }</span>
                <div class="text-right">
                    <div class="font-mono text-sm text-gray-200">${fmt.format(
                      asset.price
                    )}</div>
                    <div class="text-xs font-bold ${colorClass}">
                        ${arrow} ${sign}${asset.change.toFixed(2)}%
                    </div>
                </div>
            </div>
        `;
  });

  listHtml += "</div>";

  div.innerHTML = header + listHtml;
  return div;
}
