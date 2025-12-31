const API_BASE = "http://127.0.0.1:8000";

// Detecta qual página está aberta
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("portfolioList")) {
    loadPortfolios();
  }
  if (document.getElementById("assetsTable")) {
    loadPortfolioDetails();
  }
});

// --- PÁGINA 1: LISTA DE CARTEIRAS ---

async function createPortfolio() {
  const name = document.getElementById("newPortfolioName").value;
  if (!name) return alert("Digite um nome!");

  try {
    const res = await fetch(`${API_BASE}/portfolios/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      document.getElementById("newPortfolioName").value = "";
      loadPortfolios();
    } else {
      alert("Erro ao criar (Nome duplicado?)");
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadPortfolios() {
  const res = await fetch(`${API_BASE}/portfolios/`);
  const data = await res.json();
  const list = document.getElementById("portfolioList");
  list.innerHTML = "";

  data.forEach((p) => {
    list.innerHTML += `
            <div onclick="openPortfolio(${p.id}, '${p.name}')" class="bg-gray-800 p-6 rounded-xl border border-gray-700 hover:border-blue-500 cursor-pointer transition shadow-lg group">
                <div class="flex justify-between items-center">
                    <h3 class="text-xl font-bold text-white group-hover:text-blue-400">${p.name}</h3>
                    <span class="text-2xl">📂</span>
                </div>
                <p class="text-gray-500 text-xs mt-2">ID: ${p.id}</p>
            </div>
        `;
  });
}

function openPortfolio(id, name) {
  // Salva ID para a próxima página usar
  localStorage.setItem("currentPortfolioId", id);
  localStorage.setItem("currentPortfolioName", name);
  window.location.href = "/app/portfolio_detail.html";
}

// --- PÁGINA 2: DETALHES DA CARTEIRA ---

async function loadPortfolioDetails() {
  const id = localStorage.getItem("currentPortfolioId");
  const name = localStorage.getItem("currentPortfolioName");

  if (!id) return (window.location.href = "/app/portfolios.html");

  document.getElementById("pName").innerText = name;

  // Mostra loading na tabela
  const tbody = document.getElementById("assetsTable");
  tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-gray-500 animate-pulse">Consultando B3 em tempo real...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/portfolios/${id}/view`);
    const assets = await res.json();

    tbody.innerHTML = "";
    const fmt = new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    });

    if (assets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-gray-500">Nenhum ativo cadastrado nesta carteira.</td></tr>`;
      return;
    }

    assets.forEach((a) => {
      const isProfit = a.profit_pct >= 0;
      const profitClass = isProfit ? "text-green-400" : "text-red-400";
      const profitSign = isProfit ? "+" : "";

      tbody.innerHTML += `
                <tr class="hover:bg-gray-750 transition">
                    <td class="p-4 font-bold text-white">${a.ticker}</td>
                    <td class="p-4 text-right text-gray-300">${fmt.format(
                      a.avg_price
                    )}</td>
                    <td class="p-4 text-right font-mono text-lg text-white">${fmt.format(
                      a.current_price
                    )}</td>
                    <td class="p-4 text-right text-red-300 text-xs">${fmt.format(
                      a.low_52k
                    )}</td>
                    <td class="p-4 text-right text-green-300 text-xs">${fmt.format(
                      a.high_52k
                    )}</td>
                    <td class="p-4 text-right font-bold ${profitClass}">${profitSign}${a.profit_pct.toFixed(
        2
      )}%</td>
                    <td class="p-4 text-center">
                        <button onclick="deleteAsset(${
                          a.id
                        })" class="text-red-500 hover:text-red-300 text-xs uppercase font-bold">Excluir</button>
                    </td>
                </tr>
            `;
    });
  } catch (e) {
    console.error(e);
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-red-500">Erro ao carregar dados.</td></tr>`;
  }
}

async function addAsset() {
  const id = localStorage.getItem("currentPortfolioId");
  const ticker = document.getElementById("addTicker").value;
  const avg_price = document.getElementById("addPrice").value;

  if (!ticker || !avg_price) return alert("Preencha tudo!");

  await fetch(`${API_BASE}/portfolios/${id}/assets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, avg_price }),
  });

  document.getElementById("addTicker").value = "";
  document.getElementById("addPrice").value = "";
  loadPortfolioDetails(); // Recarrega tabela
}

async function deleteAsset(assetId) {
  if (!confirm("Remover este ativo da carteira?")) return;
  await fetch(`${API_BASE}/assets/${assetId}`, { method: "DELETE" });
  loadPortfolioDetails();
}
