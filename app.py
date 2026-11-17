import os
import telebot
import yfinance as yf
from flask import Flask, request
from datetime import datetime

TOKEN_BOT = os.environ.get("TOKEN_BOT", "8977597026:AAFFJFFX5lliVcg5wfhphhrd0FHz-XzsR_A")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))

bot = telebot.TeleBot(TOKEN_BOT, threaded=True)
app = Flask(__name__)

def calcular_painel_abertura():
    tickers = {
        "EWZ": "EWZ",
        "PBR": "PBR",
        "VALE": "VALE",
        "SP_FUT": "ES=F",
        "DOLAR": "BRL=X"
    }
    pontuacao = 0
    detalhes = []

    for nome, ticker in tickers.items():
        try:
            ativo = yf.Ticker(ticker)
            dados = ativo.history(period="1d")
            if dados.empty:
                continue

            preco_atual = dados['Close'].iloc[-1]
            preco_anterior = dados['Open'].iloc[-1]
            variacao = ((preco_atual - preco_anterior) / preco_anterior) * 100

            if nome == "EWZ":
                peso = 30
                sinal = 1 if variacao > 0 else -1
                pontuacao += peso * sinal
            elif nome in ["PBR", "VALE"]:
                peso = 20
                sinal = 1 if variacao > 0 else -1
                pontuacao += peso * sinal
            elif nome == "SP_FUT":
                peso = 15
                sinal = 1 if variacao > 0 else -1
                pontuacao += peso * sinal
            elif nome == "DOLAR":
                peso = 15
                sinal = -1 if variacao > 0 else 1
                pontuacao += peso * sinal

            emoji = "🟢" if (sinal == 1 and nome != "DOLAR") or (sinal == -1 and nome == "DOLAR") else "🔴"
            detalhes.append(f"{emoji} {nome}: {variacao:+.2f}%")
        except Exception as e:
            print(f"⚠️ Erro ao processar ativo {nome}: {e}")
            continue

    if pontuacao >= 80:
        status = "🟢 COMPRA FORTE (Alinhamento Total / Tendência)"
    elif pontuacao >= 50:
        status = "🟢 COMPRA MODERADA (Alinhamento de Risco)"
    elif pontuacao >= 15:
        status = "🟡 COMPRA LEVE (Mercado Misto / Alvo Curto)"
    elif pontuacao <= -80:
        status = "🔴 VENDA FORTE (Pânico Global)"
    elif pontuacao <= -50:
        status = "🔴 VENDA MODERADA (Fluxo Vendedor)"
    elif pontuacao <= -15:
        status = "🟡 VENDA LEVE (Realização Sutil)"
    else:
        status = "⚪️ MERCADO NEUTRO (Indefinição)"

    hora_atual = datetime.now().strftime("%H:%M")
    mensagem = (
        f"📊 <b>PAINEL DE ABERTURA DOS MINIS - {hora_atual}</b>\n\n"
        f"🏆 <b>SINAL: {status}</b>\n"
        f"🧮 Pontuação IPA: {pontuacao:+.0f} pontos\n\n"
        f"<b>Status dos Ativos:</b>\n" + "\n".join(detalhes) + "\n\n"
        f"-----------------------------------------\n"
        f"💡 <i>Foque no Mini Índice. Siga o gerenciamento de risco!</i>"
    )
    return mensagem

@bot.message_handler(commands=['start'])
def enviar_boas_vindas(message):
    usuario = message.from_user.first_name if message.from_user.first_name else "Investidor"
    boas_vindas = (
        f"👋 Olá, <b>{usuario}</b>! Seja bem-vindo ao Bot de Análise de Mercado.\n\n"
        "Aqui estão os comandos que você pode utilizar:\n"
        "📊 /analise - Calcula e gera o relatório IPA em tempo real.\n"
        "ℹ️ /ajuda - Exibe a lista completa de recursos do bot.\n"
        "📊 /ticker &lt;codigo&gt; - Consulta cotação individual."
    )
    bot.reply_to(message, boas_vindas, parse_mode="HTML")

@bot.message_handler(commands=['analise'])
def responder_analise(message):
    try:
        aguarde_msg = bot.reply_to(message, "🔄 Buscando dados de Nova York e calculando o painel... Aguarde.")
        relatorio = calcular_painel_abertura()
        bot.send_message(message.chat.id, relatorio, parse_mode="HTML")
        try:
            bot.delete_message(message.chat.id, aguarde_msg.message_id)
        except:
            pass
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao gerar o painel: {str(e)}")

@bot.message_handler(commands=['help', 'ajuda'])
def enviar_ajuda(message):
    texto_ajuda = (
        "🤖 <b>Guia de Comandos do Bot de Análise</b>\n\n"
        "/start - Inicia o bot e exibe as boas-vindas.\n"
        "/analise - Gera o relatório IPA completo com os principais ativos.\n"
        "/ticker &lt;codigo&gt; - Consulta o preço de um ativo específico (Ex: &lt;code&gt;/ticker PETR4.SA&lt;/code&gt;).\n\n"
        "<i>Dica: Sempre adicione o sufixo .SA para ações brasileiras no Yahoo Finance!</i>"
    )
    bot.reply_to(message, texto_ajuda, parse_mode="HTML")

@bot.message_handler(commands=['ticker'])
def buscar_ticker_especifico(message):
    try:
        partes = message.text.split()
        if len(partes) < 2:
            bot.reply_to(message, "⚠️ Uso: &lt;code&gt;/ticker PETR4.SA&lt;/code&gt;", parse_mode="HTML")
            return
        ticker_usuario = partes[1].upper()
        ativo = yf.Ticker(ticker_usuario)
        dados = ativo.history(period="1d")
        if dados.empty:
            bot.reply_to(message, f"❌ Não encontrei dados para {ticker_usuario}.", parse_mode="HTML")
            return

        preco_atual = dados['Close'].iloc[-1]
        preco_abertura = dados['Open'].iloc[-1]
        variacao = ((preco_atual - preco_abertura) / preco_abertura) * 100
        emoji = "🟢" if variacao >= 0 else "🔴"
        moeda = "R$" if ".SA" in ticker_usuario else "$"

        resposta = (
            f"📈 <b>Cotação de {ticker_usuario}</b>\n"
            f"---------------------------------\n"
            f"💵 Preço Atual: {moeda} {preco_atual:.2f}\n"
            f"{emoji} Variação Diária: {variacao:+.2f}%\n"
            f"---------------------------------\n"
            f"ℹ️ <i>Dados fornecidos pelo Yahoo Finance.</i>"
        )
        bot.reply_to(message, resposta, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao processar ticker: {str(e)}")

@app.route('/', methods=['GET'])
def home():
    return "Bot está online e operacional! 🚀", 200

@app.route(f"/{TOKEN_BOT}", methods=['POST'])
def obter_updates():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    else:
        return "Acesso Proibido", 403

if __name__ == '__main__':
    print("🛠️ Configurando Webhook...")
    try:
        bot.remove_webhook()
        if WEBHOOK_URL and "sua-url-aqui" not in WEBHOOK_URL:
            bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN_BOT}")
            print(f"⚡ Webhook ativado para: {WEBHOOK_URL}")
        else:
            print("⚠️ Executando sem variável WEBHOOK_URL.")
    except Exception as e:
        print(f"⚠️ Falha ao configurar Webhook: {e}")

    print(f"🏃 Iniciando servidor Flask na porta {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)